import maze_generator
import os

def test_export():
    print("Testing Maze Export...")
    try:
        # 1. Create and generate maze
        maze = maze_generator.Maze(5, 5)
        maze.generate()
        print("Maze generated.")
        
        # 2. Export to .dat (simulating main.py logic)
        filename = "test_maze.dat"
        if not os.path.exists('datasets'):
            os.makedirs('datasets')
        filepath = os.path.join('datasets', filename)
        maze.export_to_dat(filepath)
        
        # 3. Verify file exists and content
        if os.path.exists(filepath):
            print(f"File {filepath} created.")
            with open(filepath, 'r') as f:
                content = f.read()
                print("File content preview (first 10 lines):")
                print("\n".join(content.split('\n')[:10]))
                
                # Basic validation
                lines = content.split('\n')
                if lines[0].strip() == '30' and lines[1].strip() == '1':
                    print("Header looks correct.")
                else:
                    print("Header verification failed.")
        else:
            print(f"File {filename} not found.")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_export()
