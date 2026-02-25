import constants
import edgis_cache
import db
import ed_route

db_filename = f"{__file__.replace("src", "data").replace(".py", ".db")}"


def main(): ...


async def get_system_info(system_name):
    return ed_route.get_system_info(system_name)


async def get_all_system_names():
    return ed_route.get_all_system_names()


async def path(
    initial_system_name,
    destination_name,
    max_systems=100,
    preinit_db_filename=constants.pre_initiazlied_db_filename,
):
    return ed_route.path(
        initial_system_name, destination_name, max_systems, preinit_db_filename
    )


if __name__ == "__main__":
    main()
