import csv
import subprocess
import os

def run_simulation(scheduler_type):
    # Modify simulate.py to use the correct scheduler
    with open('simulate.py', 'r') as f:
        content = f.read()
        
    if scheduler_type == "baseline":
        content = content.replace('self.scheduler = GreedyScheduler()', 'self.scheduler = None')
        content = content.replace('self.scheduler = DPScheduler()', 'self.scheduler = None')
    elif scheduler_type == "greedy":
        content = content.replace('self.scheduler = None', 'self.scheduler = GreedyScheduler()')
        content = content.replace('self.scheduler = DPScheduler()', 'self.scheduler = GreedyScheduler()')
    elif scheduler_type == "dp":
        content = content.replace('self.scheduler = None', 'self.scheduler = DPScheduler()')
        content = content.replace('self.scheduler = GreedyScheduler()', 'self.scheduler = DPScheduler()')
        
    with open('simulate.py', 'w') as f:
        f.write(content)
        
    # Run simulation
    result = subprocess.run(['python', 'simulate.py'], capture_output=True, text=True)
    
    # Parse results
    stats = {}
    for line in result.stdout.split('\n'):
        if "Total Passengers Generated:" in line:
            stats['generated'] = int(line.split(': ')[1])
        elif "Total Passengers Transported:" in line:
            stats['transported'] = int(line.split(': ')[1].split(' ')[0])
        elif "Total Passengers Left at Stops:" in line:
            stats['stranded'] = int(line.split(': ')[1])
        elif "Average Wait Time (Transported):" in line:
            stats['avg_wait'] = float(line.split(': ')[1].replace(' mins', ''))
        elif "Median Wait Time (Transported):" in line:
            stats['med_wait'] = float(line.split(': ')[1].replace(' mins', ''))
        elif "Total Reallocations by Scheduler:" in line:
            stats['reallocations'] = int(line.split(': ')[1])
        elif "Scheduler Execution Time:" in line:
            stats['runtime'] = float(line.split(': ')[1].replace(' seconds', ''))
            
    # Default for baseline
    if 'reallocations' not in stats:
        stats['reallocations'] = 0
    if 'runtime' not in stats:
        stats['runtime'] = 0.0
        
    return stats

def main():
    print("Running Baseline...")
    base_stats = run_simulation("baseline")
    
    print("Running Greedy...")
    greedy_stats = run_simulation("greedy")
    
    print("Running DP...")
    dp_stats = run_simulation("dp")
    
    # Export to CSV
    csv_file = 'results.csv'
    headers = ['Scenario', 'Generated', 'Transported', 'Stranded', 'Avg Wait (mins)', 'Median Wait (mins)', 'Reallocations', 'Runtime (s)']
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        writer.writerow({'Scenario': 'Baseline', 'Generated': base_stats['generated'], 'Transported': base_stats['transported'], 'Stranded': base_stats['stranded'], 'Avg Wait (mins)': base_stats['avg_wait'], 'Median Wait (mins)': base_stats['med_wait'], 'Reallocations': base_stats['reallocations'], 'Runtime (s)': base_stats['runtime']})
        writer.writerow({'Scenario': 'Greedy', 'Generated': greedy_stats['generated'], 'Transported': greedy_stats['transported'], 'Stranded': greedy_stats['stranded'], 'Avg Wait (mins)': greedy_stats['avg_wait'], 'Median Wait (mins)': greedy_stats['med_wait'], 'Reallocations': greedy_stats['reallocations'], 'Runtime (s)': greedy_stats['runtime']})
        writer.writerow({'Scenario': 'Dynamic Programming', 'Generated': dp_stats['generated'], 'Transported': dp_stats['transported'], 'Stranded': dp_stats['stranded'], 'Avg Wait (mins)': dp_stats['avg_wait'], 'Median Wait (mins)': dp_stats['med_wait'], 'Reallocations': dp_stats['reallocations'], 'Runtime (s)': dp_stats['runtime']})
        
    print(f"Results exported successfully to {csv_file}")

if __name__ == "__main__":
    main()
