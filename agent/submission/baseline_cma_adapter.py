import copy
from typing import Any, Dict

import torch
from habitat_baselines.common.baseline_registry import baseline_registry
from habitat_baselines.utils.common import batch_obs

from vlnce_baselines.common.utils import extract_instruction_tokens


def build_agent(agent_config: Dict[str, Any], runtime_spec: Dict[str, Any]):
    return BaselinePolicyAgent(agent_config, runtime_spec)


class BaselinePolicyAgent:
    def __init__(self, agent_config: Dict[str, Any], runtime_spec: Dict[str, Any]):
        self.device = runtime_spec["device"]
        self.allowed_actions = runtime_spec["allowed_actions"]
        self.instruction_sensor_uuid = runtime_spec["instruction_sensor_uuid"]
        self.policy_config = runtime_spec["policy_config"].clone()
        self.observation_space = runtime_spec["observation_space"]
        self.action_space = runtime_spec["action_space"]
        self.policy_name = agent_config.get(
            "POLICY_NAME", self.policy_config.MODEL.policy_name
        )
        self.checkpoint_path = agent_config.get("CKPT_PATH")
        assert self.checkpoint_path, "CHALLENGE_AGENT.CONFIG.CKPT_PATH must be set."

        policy_cls = baseline_registry.get_policy(self.policy_name)
        assert policy_cls is not None, f"Unsupported policy {self.policy_name!r}."
        self.policy = policy_cls.from_config(
            self.policy_config,
            observation_space=self.observation_space,
            action_space=self.action_space,
        )
        self.policy.to(self.device)
        self._load_checkpoint()
        self.policy.eval()

        self.hidden_size = self.policy_config.MODEL.STATE_ENCODER.hidden_size
        self.rnn_states = None
        self.prev_actions = None
        self.not_done_masks = None
        self.reset({})

    def reset(self, episode: Dict[str, Any]) -> None:
        del episode
        self.rnn_states = torch.zeros(
            1,
            self.policy.net.num_recurrent_layers,
            self.hidden_size,
            device=self.device,
        )
        self.prev_actions = torch.zeros(
            1, 1, device=self.device, dtype=torch.long
        )
        self.not_done_masks = torch.zeros(
            1, 1, dtype=torch.uint8, device=self.device
        )

    def act(self, observation: Dict[str, Any]) -> str:
        observations = extract_instruction_tokens(
            [copy.deepcopy(observation)], self.instruction_sensor_uuid
        )
        batch = batch_obs(observations, self.device)
        with torch.no_grad():
            action_tensor, self.rnn_states = self.policy.act(
                batch,
                self.rnn_states,
                self.prev_actions,
                self.not_done_masks,
                deterministic=True,
            )
        self.prev_actions.copy_(action_tensor)
        self.not_done_masks.fill_(1)
        action_index = action_tensor.item()
        assert 0 <= action_index < len(self.allowed_actions), (
            f"Policy returned invalid action index {action_index}. "
            f"Allowed range: [0, {len(self.allowed_actions) - 1}]"
        )
        return self.allowed_actions[action_index]

    def close(self) -> None:
        return None

    def _load_checkpoint(self) -> None:
        checkpoint = torch.load(self.checkpoint_path, map_location="cpu")
        assert "state_dict" in checkpoint, (
            f"Checkpoint {self.checkpoint_path!r} does not contain 'state_dict'."
        )
        state_dict = checkpoint["state_dict"]
        model_state = self.policy.state_dict()
        mismatched_keys = []
        for key, value in list(state_dict.items()):
            if key not in model_state:
                continue
            if model_state[key].shape != value.shape:
                mismatched_keys.append(key)
                del state_dict[key]

        missing_keys, unexpected_keys = self.policy.load_state_dict(
            state_dict, strict=False
        )
        critical_missing = [
            key
            for key in missing_keys
            if key not in mismatched_keys
            and "instruction_encoder.embedding_layer.weight" not in key
        ]
        assert not unexpected_keys, (
            f"Checkpoint {self.checkpoint_path!r} has unexpected keys: "
            f"{unexpected_keys}"
        )
        assert not critical_missing, (
            f"Checkpoint {self.checkpoint_path!r} is missing required keys: "
            f"{critical_missing}"
        )
