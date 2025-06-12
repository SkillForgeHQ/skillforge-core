from collections import deque

# skill_graph.py

# This is an adjacency list representation of the SkillForge data model.
# The key is the skill (a node).
# The value is a list of its prerequisites (the nodes that have an edge leading to the key).

skill_graph = {
    'Set Table': ['Know Place Setting Layout', 'Place Objects', 'Walk'],
    'Know Place Setting Layout': ['ID Fork', 'ID Spoon', 'ID Knife', 'ID Napkin', 'ID Plate', 'ID Glass'],
    'Place Objects': ['Grasp Small Object', 'ID Fork', 'ID Spoon', 'ID Knife', 'ID Napkin', 'ID Plate', 'ID Glass', 'Walk', 'Coordinate Limbs'],
    'Locate Table': ['See Objects'],
    'Grasp Small Object': ['See Objects', 'Coordinate Limbs'],
    'ID Fork': ['See Objects'],
    'ID Spoon': ['See Objects'],
    'ID Knife': ['See Objects'],
    'ID Napkin': ['See Objects'],
    'ID Plate': ['See Objects'],
    'ID Glass': ['See Objects'],
    'See Objects': [],
    'Walk': ['Crawl'],
    'Crawl': ['Coordinate Limbs'],
    'Coordinate Limbs': []
}

# You can add a print statement to test it out
if __name__ == '__main__':
    import json
    #print(json.dumps(skill_graph, indent=2))

# Function to find BFS of Graph from given source s

# Function to find BFS of Graph from a given source s
def bfs(adj, s):
    # create a set to store visited nodes
    visited = set()

    # create a queue for BFS
    q = deque()

    # Mark source node as visited and enqueue it
    visited.add(s)
    q.append(s)

    # The result list to store the traversal order
    res = []

    # Iterate over the queue
    while q:
        # Dequeue a vertex from queue and add it to the result
        curr = q.popleft()
        res.append(curr)

        # Get all prerequisites of the current skill.
        # If a prerequisite has not been visited,
        # mark it visited and enqueue it.
        for prereq in adj.get(curr, []): # Use .get() for safety
            if prereq not in visited:
                visited.add(prereq)
                q.append(prereq)

    return res


if __name__ == "__main__":
    # Your skill_graph dictionary is defined above

    start_node = 'Set Table'
    print(f"Finding all prerequisites for '{start_node}' via BFS:")

    # Run the corrected BFS
    prerequisites = bfs(skill_graph, start_node)

    print(" -> ".join(prerequisites))


def dfs_iterative(adj, start_node):
    visited = set()
    stack = [start_node]
    res = []

    while stack:
        # Pop a vertex from the top of the stack
        curr = stack.pop()

        if curr not in visited:
            res.append(curr)
            visited.add(curr)

            # Add all unvisited prerequisites to the top of the stack
            # Note: We access neighbors with adj[curr]
            for prereq in adj.get(curr, []):
                if prereq not in visited:
                    stack.append(prereq)
    return res

# We use a helper function to pass the 'visited' set through the recursive calls.
def dfs_recursive(adj, start_node):
    visited = set()
    res = []

    def _dfs_helper(node):
        # Mark the current node as visited and add to result
        visited.add(node)
        res.append(node)

        # Recur for all unvisited prerequisites
        for prereq in adj.get(node, []):
            if prereq not in visited:
                _dfs_helper(prereq)

    # Kick off the recursion
    _dfs_helper(start_node)
    return res

if __name__ == "__main__":
    # Your skill_graph dictionary is defined above...

    start_node = 'Set Table'

    print("--- Iterative DFS ---")
    path1 = dfs_iterative(skill_graph, start_node)
    print(" -> ".join(path1))

    print("\n--- Recursive DFS ---")
    path2 = dfs_recursive(skill_graph, start_node)
    print(" -> ".join(path2))