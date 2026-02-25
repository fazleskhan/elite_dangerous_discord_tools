import db
import edgis_cache


def main(): ...


def database(database_filename):
    return db.DB(database_filename)


def ed(database_filename):
    database = db.DB(database_filename)
    return edgis_cache.Ed_Cache(database)


if __name__ == "__main__":
    main()
