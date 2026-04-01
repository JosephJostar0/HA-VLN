# HA-VLN Challenge - Quick Start

Get up and running in 5 minutes!

## 1️⃣ Understand the Submission Format (2 min)

```bash
cat challenge/SUBMISSION_FORMAT.md
```

**Key Points**:
- Submit JSON with action sequences
- Actions: 0=STOP, 1=MOVE, 2=LEFT, 3=RIGHT
- 3408 episodes, must end with STOP
- See `examples/` for templates

## 2️⃣ View Examples (1 min)

```bash
ls -lh challenge/examples/
cat challenge/examples/random_baseline.json | head -30
```

**Three examples**:
- `random_baseline.json` - Random actions
- `forward_walk.json` - Always move forward
- `il_baseline.json` - Realistic learned model

## 3️⃣ Generate Your First Submission (1 min)

### Option A: Using template

```bash
cd /home/jojo/gitlib/HA-VLN

python challenge/template_solution.py \
  --output my_submission.json \
  --policy forward \
  --team-name "My Team"
```

### Option B: Minimal Python

```python
import json
import gzip

# Load test split
with gzip.open('Data/HA-R2R/test.json.gz') as f:
    test = json.load(f)

# Generate actions
episodes = []
for ep in test['episodes']:
    actions = [1] * 20 + [0]  # Move 20 times, then stop
    episodes.append({
        "episode_id": str(ep["episode_id"]),
        "trajectory_id": ep["trajectory_id"],
        "scene_id": ep["scene_id"],
        "actions": actions
    })

# Save
with open('my_submission.json', 'w') as f:
    json.dump({"episodes": episodes}, f)
```

## 4️⃣ Validate Submission (1 min)

```bash
# Quick check: Episode count
python -c "import json; \
data = json.load(open('my_submission.json')); \
print(f\"Episodes: {len(data['episodes'])}\")"

# Should print: Episodes: 3408
```

## 5️⃣ Run Evaluator (optional)

```bash
# Only works if evaluator is set up
python challenge/evaluator.py my_submission.json --output results/

# View results
cat results/summary.txt
cat results/leaderboard.json
```

## 📚 After Quick Start

| Goal | Read |
|------|------|
| Understand scoring | `challenge/EVALUATION_GUIDE.md` |
| Submit to leaderboard | `challenge/SUBMISSION_FORMAT.md` |
| Develop better model | `challenge/STARTER_KIT.md` |
| Troubleshoot | `challenge/SUBMISSION_FORMAT.md` FAQ section |

## 🎯 Typical Development Flow

```bash
# 1. Develop
python my_model.py --output submission_v1.json

# 2. Validate locally
python -c "
import json
data = json.load(open('submission_v1.json'))
assert len(data['episodes']) == 3408
assert all(1 <= len(e['actions']) <= 500 for e in data['episodes'])
assert all(e['actions'][-1] == 0 for e in data['episodes'])
print('✓ Validation passed')
"

# 3. Submit
# (Upload to leaderboard website)

# 4. Monitor results
# (Check leaderboard)

# 5. Iterate
# Improve model, go to step 1
```

## ✅ Checklist

- [ ] Read SUBMISSION_FORMAT.md
- [ ] Install requirements: `pip install -r challenge/requirements.txt`
- [ ] View examples: `ls challenge/examples/`
- [ ] Generate submission: `python challenge/template_solution.py ...`
- [ ] Validate: Episode count = 3408, actions in [0,1,2,3], last = 0
- [ ] Submit to leaderboard

## ❓ Common Questions

**Q: What's the difference between random_baseline.json and forward_walk.json?**  
A: Random samples actions 0-3. Forward always moves forward. See examples.

**Q: How many actions per episode:**  
A: Between 1-500. Must end with action 0 (STOP).

**Q: Can I use Habitat simulator:**  
A: Yes! See `challenge/STARTER_KIT.md` "Integration with Habitat"

**Q: How are submissions scored:**  
A: See `challenge/EVALUATION_GUIDE.md` for full metric descriptions

**Q: What's SR_human:**  
A: Success Rate accounting for human collisions. Primary ranking metric.

## 🚀 Next Steps

1. Generate your first submission (5 min)
2. Review metrics in EVALUATION_GUIDE.md (10 min)
3. Develop your model (hours/days)
4. Monitor leaderboard (ongoing)

**Good luck! 🏆**

---

Questions? See:
- Format → `SUBMISSION_FORMAT.md`
- Metrics → `EVALUATION_GUIDE.md`
- Development → `STARTER_KIT.md`
