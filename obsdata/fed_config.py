import os
import csv
from collections import namedtuple


DATADIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data"
)


SiteInfo = namedtuple(
    "SiteInfo",
    [
        "id",
        "code",
        "name",
        "country",
        "state",
        "latitude",
        "longitude",
        "elevation",
        "start",
        "end",
    ]
)


ParameterInfo = namedtuple(
    "ParameterInfo", ["id", "code"]
)


DatasetConfig = namedtuple(
    "DatasetConfig",
    ["name", "time_interval", "site_file", "parameter_file"]
)


class InputError(Exception):
    pass


def get_datasets():
    '''return a dictionary of all fed datasets
    '''
    dataset_file = os.path.join(DATADIR, 'datasets.csv')
    datasets = {}
    with open(dataset_file, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for line_count, row in enumerate(csv_reader):
            if line_count > 0:
                datasets[row[0]] = DatasetConfig(
                    name=row[1],
                    time_interval=row[2],
                    site_file=os.path.join(
                        DATADIR,
                        "fedsites_{}.csv".format(row[0])
                    ),
                    parameter_file=os.path.join(
                        DATADIR,
                        "parameters_{}.csv".format(row[0])
                    ),
                )
    return datasets


def get_site_info(dataset, site_code):
    '''returns an instance of SiteInfo with data
       as contained in the site file
    '''
    with open(datasets[dataset].site_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if row[1] == site_code:
                return SiteInfo(
                    id=row[0],
                    code=row[1],
                    name=row[2],
                    country=row[3],
                    state=row[4],
                    latitude=row[6],
                    longitude=row[7],
                    elevation=row[8],
                    start=row[9],
                    end=row[10],
                )
    print("site_code {0} not found for dataset {1}".format(
        site_code, dataset))
    with open(datasets[dataset].site_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        print("available sites are:")
        for row in csv_reader:
            print("{0} for {1}".format(row[1], row[2]))

    raise(InputError)


def get_all_site_codes(dataset_id):
    '''returns a list containing all site codes
       (e.g. BADL1)
       of the site file of the dataset
    '''
    site_codes = []
    with open(datasets[dataset_id].site_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for line_count, row in enumerate(csv_reader):
            if line_count > 0:
                site_codes.append(row[1])
    return site_codes


def get_parameter_info(dataset_id, parameter_code):
    '''returns an instance of ParameterInfo
       as defined by the parameter file
    '''
    with open(datasets[dataset_id].parameter_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if row[0] == parameter_code:

                return ParameterInfo(id=row[1], code=row[0])
        print("parameter_code {0} not found for dataset {1}".format(
            parameter_code, datasets[dataset_id].name))
    with open(datasets[dataset_id].parameter_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        print("available parameters are:")
        for row_nr, row in enumerate(csv_reader):
            if row_nr > 0:
                print("{}".format(row[0]))
    raise(InputError)


def get_all_parameters(dataset_id):
    '''returns a list of ParameterInfo
       as defined by the parameter file
    '''
    parameters = []
    with open(datasets[dataset_id].parameter_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for line_count, row in enumerate(csv_reader):
            if line_count > 0:
                parameters.append(
                    ParameterInfo(id=row[1], code=row[0])
                )
    return parameters


def validate_input(dataset_id, site, parameter):
    '''checks that input is valid'''
    # dataset
    if dataset_id not in datasets.keys():
        print(
            'dataset {} is not implemented.\n'.format(dataset_id) +
            'implemented datasets are:'
        )
        for dataset in datasets.keys():
            print("{} for '{}'".format(
                dataset,
                datasets[dataset].name))
        raise(InputError)

    # get_site_info raises if site not found
    get_site_info(dataset_id, site)

    # get_parameter_info raises if site not found
    get_parameter_info(dataset_id, parameter)

    return True


datasets = get_datasets()
