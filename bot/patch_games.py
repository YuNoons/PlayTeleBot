import os
import glob
import re

base_dir = os.path.dirname(os.path.abspath(__file__))
files = glob.glob(os.path.join(base_dir, 'games', '*.py')) + [os.path.join(base_dir, 'handlers', 'common.py')]

for f in files:
    with open(f, 'r') as file:
        content = file.read()
    
    # We replace:
    # if not game or game["state"] != "...":
    #     return await call.answer("...", show_alert=True)
    
    # Also find: if not game: \n return await call.answer(...)
    
    pattern = r'(if not game(?: or .*?)?:\s*)(return await call\.answer\(.*?\))'
    
    def replacer(match):
        cond = match.group(1)
        ans = match.group(2)
        
        if 'not game' in cond:
            if 'or game["state"]' in cond or 'and game["state"]' in cond:
                # split the condition
                state_cond = cond.replace('not game or ', '').replace('not game and ', '')
                return f"""if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    {state_cond}{ans}"""
            else:
                return f"""if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)"""
        return match.group(0)

    new_content = re.sub(pattern, replacer, content)
    
    # Also handle join_game in common.py where it's:
    # if not game or game["state"] != "waiting":
    
    with open(f, 'w') as file:
        file.write(new_content)

print("Patched!")
