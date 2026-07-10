import subprocess

def modify_multiplier(old_val, new_val):
    with open('simulate.py', 'r') as f:
        content = f.read()
    
    content = content.replace(f'TARGET_DEMAND_MULTIPLIER = {old_val}', f'TARGET_DEMAND_MULTIPLIER = {new_val}')
    
    with open('simulate.py', 'w') as f:
        f.write(content)

def modify_scheduler(sched):
    with open('simulate.py', 'r') as f:
        content = f.read()
    
    # reset both
    content = content.replace('self.scheduler = GreedyScheduler()', 'self.scheduler = None')
    content = content.replace('self.scheduler = DPScheduler()', 'self.scheduler = None')
    
    if sched == "Greedy":
        content = content.replace('self.scheduler = None', 'self.scheduler = GreedyScheduler()')
    elif sched == "DP":
        content = content.replace('self.scheduler = None', 'self.scheduler = DPScheduler()')
        
    with open('simulate.py', 'w') as f:
        f.write(content)

def run_sim():
    result = subprocess.run(['python', 'simulate.py'], capture_output=True, text=True)
    transported = 0
    realloc = 0
    for line in result.stdout.split('\n'):
        if "Total Passengers Transported:" in line:
            transported = int(line.split(': ')[1].split(' ')[0])
        elif "Total Reallocations by Scheduler:" in line:
            realloc = int(line.split(': ')[1])
    return transported, realloc

def main():
    print("Artificially cranking up contention to 3.0x capacity demand...")
    modify_multiplier('1.2', '3.0')
    
    print("Running Greedy...")
    modify_scheduler("Greedy")
    g_trans, g_real = run_sim()
    print(f"Greedy: {g_trans} transported, {g_real} reallocations")
    
    print("Running DP...")
    modify_scheduler("DP")
    dp_trans, dp_real = run_sim()
    print(f"DP: {dp_trans} transported, {dp_real} reallocations")
    
    # Restore
    modify_multiplier('3.0', '1.2')
    print("Restored original multiplier.")

if __name__ == "__main__":
    main()
