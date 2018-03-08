from sqlalchemy import create_engine
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')


# Find party affiliation for favorites using legislator data in postgres
def db_create_engine(config_file, conn_name):
    """
    Create a sqlAlchemy engine to connect to Postgres database given some connection parameters in config file.
    Note - this can be used to connect to any Postgres db either remotely or locally

    :param config_file: A config file with connection configuration details under conn_name heading
    :param conn_name: The section name for set of configuration details for desired connection
    :return: A sqlAlchemy engine connected to aws postgres database
    """
    config = ConfigParser()
    config.read(config_file)

    engine = create_engine('postgresql://{}:{}@{}:{}/{}'
                           .format(config.get('{}'.format(conn_name), 'user'),
                                   config.get('{}'.format(conn_name), 'password'),
                                   config.get('{}'.format(conn_name), 'host'),
                                   config.get('{}'.format(conn_name), 'port'),
                                   config.get('{}'.format(conn_name), 'db')))

    return engine


legislator_parties_sql = """
    SELECT 
        s.twitter_screen_name, 
        l.party
    FROM legislators l
    JOIN social s
        ON l.legislator_id = s.legislator_id
    WHERE s.twitter_screen_name <>'';
"""


def find_legislator_parties():
    """
    Take a list of twitter accounts and return a dictionary with the corresponding party label
    """
    engine = db_create_engine(config_file='config.ini', conn_name='PostgresConfig')
    result = engine.execute(legislator_parties_sql)
    party_dict = {row[0]: row[1] for row in result}

    return party_dict
