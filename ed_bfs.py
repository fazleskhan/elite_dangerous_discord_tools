from collections import deque
import constants


def main(): ...


def travel(
    func_fetch_info, func_fetch_neighbors, start_name, destination_name="", max_count=10
):

    if start_name == destination_name:
        return [start_name]

    node_count = 0

    queue = deque([[start_name]])
    visited = set([start_name])

    while queue:

        # stop traveling
        if node_count > max_count:
            print("max number of systems: ", max_count)
            break
        else:
            node_count += 1

        path = queue.popleft()
        current_node = path[-1]

        if current_node == destination_name:
            return path

        system_info = func_fetch_info(current_node)

        # retrieve adjacent systems from edgris
        for adjacent_neighbor in func_fetch_neighbors(system_info):
            if adjacent_neighbor[constants.system_info_name_field] not in visited:
                adjacent_neighbor = func_fetch_info(
                    adjacent_neighbor[constants.system_info_name_field]
                )
                visited.add(adjacent_neighbor[constants.system_info_name_field])
                new_path = list(path)
                new_path.append(adjacent_neighbor[constants.system_info_name_field])
                queue.append(new_path)


if __name__ == "__main__":
    main()
