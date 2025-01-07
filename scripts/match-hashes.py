#! /usr/bin/env nix-shell
#! nix-shell -i python3 shell.nix


import json
import sys
import os
import shutil

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


hashes_json = sys.argv[1]
world_files = sys.argv[2]
new_world_files = sys.argv[3]

hashes = json.load(open(hashes_json, 'r'))

worlds = [os.path.splitext(f)[0] for f in os.listdir(world_files)]
new_worlds = [os.path.splitext(f)[0] for f in os.listdir(new_world_files)]

print(len(worlds))

#print(hashes)
#print(worlds[:10])

count = 0
for w in worlds:
    if w in hashes:
        count +=1
        new_name = hashes[w]
        shutil.copyfile(world_files + '/' + w + ".pgw", new_world_files + '/' + new_name + ".pgw")
    else:
        eprint("MISS", w)


eprint(count, len(worlds))

