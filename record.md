## 新增ETPNav的Baseline

### Dependency
- ETPNav源码里的models/etp/这个目录复制到本项目的agent/VLN-CE/vlnce_baselines/models/下
- 修改ETPNav的waypoint_pred。HA-VLN的waypoint在models/waypoint_predictors.py里
- 在agent/VLN-CE/vlnce_baselines/models/utils.py里添加ETPNav需要的函数
- 会用到openai的clip，Please run: `pip install ftfy regex tqdm` and then `pip install git+https://github.com/openai/CLIP.git --no-deps`
- 在agent/VLN-CE/vlnce_baselines/__init__.py里添加ETPNav的policy
- vlnce_baselines/common/下缺少的文件补全
