with open(
autodj/config.py, "r", encoding="utf-8") as f: content = f.read()
old = chr(34)+chr(34)+chr(34)+"You are AutoDJ, a music bot in a Camfrog room. Keep replies short, friendly, and on-topic. Do not claim to play music unless asked."+chr(34)+chr(34)+chr(34)
new = chr(34)+chr(34)+chr(34)+"You are AutoDJ, a music bot in a Camfrog room powered by NVIDIA AI. Keep replies short, friendly, and on-topic. Do not claim to play music unless asked."+chr(34)+chr(34)+chr(34)
if old in content: content = content.replace(old, new); f = open(
autodj/config.py, "w", encoding="utf-8"); f.write(content); f.close(); print("Updated")
