import ed_bfs
import edgis_cache
import db

db_filename = f"{__file__.replace("src", "data").replace(".py", ".db")}"


def main():
    initial_system_name = input("initial_system: ")
    number_of_systems = int(input("system_count: "))
    logic(initial_system_name, number_of_systems)


def logic(initial_system_name, number_of_systems):

    database = db.DB(db_filename)
    cache = edgis_cache.EDGisCache.create(database)

    ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        initial_system_name,
        "",
        number_of_systems,
    )


def fetch_system_info():
    return edgis_cache.find_system_info


def fetch_neighbors():
    edgis_cache.find_system_neighbors


if __name__ == "__main__":
    main()
