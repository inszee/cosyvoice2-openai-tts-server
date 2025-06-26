import torch
import pprint

pt_file = "./pretrained_models/CosyVoice2-0.5B/baiyansong_spk2info.pt"
data = torch.load(pt_file, map_location="cpu")

print(f"Type: {type(data)}")
print("Top-level keys:", list(data.keys()))
# Print the content under key "中文女"
pprint.pprint(data["中文男"])

if isinstance(data, dict):
    for k, v in data.items():
        print(f"{k}: {type(v)}")
        if hasattr(v, "shape"):
            print(f"  shape: {v.shape}")
else:
    pprint.pprint(data)