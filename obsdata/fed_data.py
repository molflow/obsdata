import os
import requests
import csv
import pkg_resources
from datetime import datetime
from bs4 import BeautifulSoup
from netCDF4 import Dataset, date2num


DATADIR = pkg_resources.resource_filename(__name__, "")


request_url = "http://views.cira.colostate.edu/fed/Reports/RawDataReport2.aspx"
datasets = {
    "improve aerosol": {
        "id": 10001,
        "df": "Daily",
        "site_file": os.path.join(DATADIR, "fedsites_improve_aerosol.csv"),
        "parameter_file": os.path.join(DATADIR, "dataset_improve_aerosol.csv"),
    },
    # castnet ozone hourly
    "castnet": {
        "id": 23005,
        "df": "Hourly",
        "site_file": os.path.join(DATADIR, "fedsites_castnet.csv"),
        "parameter_file": os.path.join(DATADIR, "dataset_castnet.csv"),
    }
}


class InputError(Exception):
    pass


def validate_input(dataset, site, parameter):

    # dataset
    if dataset not in datasets.keys():
        print(
            'dataset {} is not implemented.\n'.format(dataset) +
            'implemented datasets are:'
        )
        for dataset in datasets.keys():
            print("'{}'".format(dataset))
        raise(InputError)

    # site
    site_info = get_site_info(dataset, site)
    if not site_info:
        print(
            'site-code {} is not available.\n'.format(site) +
            'available sites are:'
        )
        site_codes = get_all_site_codes(dataset)
        for site_code in site_codes:
            site_info = get_site_info(dataset, site_code)
            print("{}: {}".format(site_code, site_info))
        raise(InputError)

    # parameter
    parameter_info = get_parameter_info(dataset, parameter)
    if not parameter_info:
        print(
            'parameter-code {} is not available.\n'.format(parameter) +
            'available parameters are:'
        )
        with open(datasets[dataset]["parameter_file"]) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                print(row)
        raise(InputError)

    return True


def set_request_data(
        dataset_id, site_id, parameter_id, df, start_date, end_date):
    return {
        "agidse": 1,
        "dt": "{0}>{1}".format(
            start_date.strftime("%Y/%m/%d"),
            end_date.strftime("%Y/%m/%d")
        ),
        "dsidse": dataset_id,
        "op": [
            "OutputFormat-AsciiText",
            "OutputMedium-File",
            "FilePartitioning-Single",
            "ColumnFormat-Delimited",
            "RowFormat-Pivot",
            "Delimiter-;",
            "ContentType-DataAndMetadata",
            "ColumnHeaders-true",
            "SectionTitles-true",
            "StringQuotes-None",
            "MissingValues--999",
            "DateFormat-101",
        ],
        "fi": [
            "Dataset.DatasetCode",
            "Site.SiteCode",
            "AirFact.POC",
            "AirFact.FactDate",
            "AirFact.FactValue"
        ],
        "siidse": site_id,
        "paidse": parameter_id,
        "df": df,
        "qscs": "load",
        "dttype": 1,
    }


def get_site_info(dataset, site_code):
    site_info = {}
    with open(datasets[dataset]["site_file"]) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for line_count, row in enumerate(csv_reader):
            if line_count == 0:
                header = row
            else:
                if row[1] == site_code:
                    for item, value in zip(header, row):
                        site_info[item] = value
    return site_info


def get_all_site_codes(dataset):
    site_codes = []
    with open(datasets[dataset]["site_file"]) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for line_count, row in enumerate(csv_reader):
            if line_count > 0:
                site_codes.append(row[1])
    return site_codes


def get_parameter_info(dataset, parameter_code):
    parameter_info = {}
    with open(datasets[dataset]["parameter_file"]) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for line_count, row in enumerate(csv_reader):
            if line_count == 0:
                header = row
            else:
                if row[2] == parameter_code:
                    for item, value in zip(header, row):
                        parameter_info[item] = value
    return parameter_info


def get_data(request_data):

    r = requests.post(request_url, data=request_data)
    soup = BeautifulSoup(r.content, 'html.parser')
    link = soup.find("a")
    href = link.get('href')
    url_base = "http://views.cira.colostate.edu"
    url_txt = url_base + href
    r_txt = requests.get(url_txt)
    return parse_fed_data(r_txt.text)


def parse_fed_data(text):

    def get_row_nr(rows, string):
        return [
            row_nr for row_nr, row in enumerate(rows) if row == string][0]

    def get_data_dict(rows):
        datadict = {}
        for item, value in zip(rows[0].split(';'), rows[1].split(';')):
            datadict[item] = value
        return datadict

    rows = text.replace("\r", '').split("\n")

    metadata = {}
    for item in ["Datasets", "Sites", "Parameters"]:
        row_nr = get_row_nr(rows, item)
        metadata[item.lower()] = get_data_dict(rows[row_nr + 2: row_nr + 4])

    data = []
    for index, row in enumerate(rows[get_row_nr(rows, "Data") + 2 : -1]):
        current_row = row.split(';')
        if index == 0:
            date_index = current_row.index("Date")
        if index > 0:
            try:
                current_row[date_index] = (
                    datetime.strptime(
                        current_row[date_index], '%m/%d/%Y %H:%M:%S'
                    )
                )
            except ValueError:
                current_row[date_index] = (
                    datetime.strptime(
                        current_row[date_index], '%m/%d/%Y')
                )
        data.append(current_row)
    dates = [row[date_index] for ind, row in enumerate(data) if ind > 0]

    return {
        "frequency": metadata["datasets"]["Frequency"],
        "site": metadata["sites"]["Site"],
        "site_code": metadata["sites"]["Code"],
        "dataset": metadata["sites"]["Dataset"],
        "state": metadata["sites"]["State"],
        "county": metadata["sites"]["County"],
        "latitude": metadata["sites"]["Latitude"],
        "longitude": metadata["sites"]["Longitude"],
        "elevation": metadata["sites"]["Elevation"],
        "start_date": metadata["sites"]["StartDate"],
        "end_date": metadata["sites"]["EndDate"],
        "num_pocs": metadata["sites"]["NumPOCs"],
        "dataset_id": metadata["parameters"]["DatasetID"],
        "parameter": metadata["parameters"]["Parameter"],
        "parameter_code": metadata["parameters"]["Code"],
        "aqs_code": metadata["parameters"]["AQSCode"],
        "units": metadata["parameters"]["Units"].replace("\xc2", ''),
        "description": metadata["parameters"]["Description"],
        "dates": dates,
        "data": data
    }


def save_data_txt(out_dir, data):
    """
        the 'World Data Centre' format is used,
        It has 32 header lines which describes the site and data,
        then the data-records.
        # TODO: fix format (talk to dave)
    """
    header_lines = 32
    title = "{0} {1} mean data".format(
        data["parameter_code"], data["frequency"])
    file_name = "{0}_{1}_{2}.dat".format(
        data["site_code"].lower(),
        data["parameter_code"].lower(),
        data["dates"][0].strftime("%Y%m%d")
    )
    data_format = "Version 1.0"  # ?
    total_lines = header_lines + len(data["data"])
    data_version = "201405"  # ?
    station_name = data["site"]
    station_category = "global"  # ?
    observation_category = (
        "Air sampling observation at a stationary platform"
    )
    country = data["state"]  # this is state, not country
    contributor = "NUI"
    latitude = data["latitude"]
    longitude = data["longitude"]
    altitude = data["elevation"]
    number_of_sampling_heights = "?"
    sampling_heights = "?"
    contact_point = "?"  # what should we have here
    parameter = data["parameter_code"]
    covering_period = "{0} {1}".format(
        data["dates"][0].strftime("%Y-%m-%d"),
        data["dates"][-1].strftime("%Y-%m-%d")
    )
    time_interval = data["frequency"]
    measurement_unit = data["units"]
    measurement_method = "Light absorption analysis (UV)"  # ?
    sampling_type = "continuous"  # ?
    measurement_scale = "National Physical Laboratory (UK)"  # ?
    file_header_rows = [
        "C01 TITLE: {}".format(title),
        "C02 FILE NAME: {}".format(file_name),
        "C03 DATA FORMAT: {}".format(data_format),
        "C04 TOTAL LINES: {}".format(total_lines),
        "C05 HEADER LINES: {}".format(header_lines),
        "C06 DATA VERSION: {}".format(data_version),
        "C07 STATION NAME: {}".format(station_name),
        "C08 STATION CATEGORY: {}".format(station_category),
        "C09 OBSERVATION CATEGORY: {}".format(observation_category),
        "C10 COUNTRY/TERRITORY: {}".format(country),
        "C11 CONTRIBUTOR: {}".format(contributor),
        "C12 LATITUDE: {}".format(latitude),
        "C13 LONGITUDE: {}".format(longitude),
        "C14 ALTITUDE: {}".format(altitude),
        "C15 NUMBER OF SAMPLING HEIGHTS: {}".format(number_of_sampling_heights),
        "C16 SAMPLING HEIGHTS: {}".format(sampling_heights),
        "C17 CONTACT POINT: {}".format(contact_point),
        "C18 PARAMETER: {}".format(parameter),
        "C19 COVERING PERIOD: {}".format(covering_period),
        "C20 TIME INTERVAL: {}".format(time_interval),
        "C21 MEASUREMENT UNIT: {}".format(measurement_unit),
        "C22 MEASUREMENT METHOD: {}".format(measurement_method),
        "C23 SAMPLING TYPE: {}".format(sampling_type),
        "C24 TIME ZONE: UTC",
        "C25 MEASUREMENT SCALE: {}".format(measurement_scale),
        "C26 CREDIT FOR USE: This is a formal notification for data users. 'For scientific purposes, access to these data is unlimited",  # noqa
        "C27 and provided without charge. By their use you accept that an offer of co-authorship will be made through personal contact",  # noqa
        "C28 with the data providers or owners whenever substantial use is made of their data. In all cases, an acknowledgement",  # noqa
        "C29 must be made to the data providers or owners and the data centre when these data are used within a publication.'",  # noqa
        "C30 COMMENT:",
        "C31",
        "C32   DATE  TIME       DATE  TIME {}".format(parameter.rjust(11)),
    ]

    with open(os.path.join(out_dir, file_name), mode='w') as outfile:
        for row in file_header_rows:
            outfile.write("{}\n".format(row))

        for index, row in enumerate(data["data"]):
            if index > 0:
                outfile.write(
                    "{0} 9999-99-99 99:99 {1}\n".format(
                        row[3].strftime("%Y-%m-%d %H:%M"), row[4].rjust(11)
                    )
                )


def save_data_netcdf(out_dir, data):

    # TODO: fix format (talk to dave)

    output_file = os.path.join(out_dir, "test.nc")
    dataset = Dataset(output_file, "w", format="NETCDF4")

    # global attributes

    dataset.station_name = data["site"]
    dataset.latitude = float(data["latitude"])
    dataset.longitude = float(data["longitude"])
    dataset.altitude = float(data["elevation"])

    # dimensions

    n = len(data["data"]) - 1
    timedim = dataset.createDimension("time", n)

    # time

    time = dataset.createVariable("time", "f8", (timedim.name,))
    time.standard_name = "time"
    time.long_name = "time of measurement"
    time.units = "days since 1900-01-01 00:00:00 UTC"
    # times.axis = "T"
    time.calendar = "gregorian"
    # times.bounds = "time_bnds"
    # times.cell_methods = "mean"
    dates = [
        datetime.combine(row[3],  datetime.min.time())
        for i, row in enumerate(data["data"]) if i > 0
    ]
    time[:] = date2num(dates, time.units, calendar=time.calendar)

    # main parameter

    parameter = dataset.createVariable(
        data["parameter_code"], "f8", (timedim.name,), fill_value=-9999.)
    parameter.standard_name = data["parameter"]
    parameter.missing_value = -9999.
    parameter.units = data["units"]
    # parameter.ancillary_variables = "?"
    # parameter.cell_methods = "time: mean" ;
    parameter[:] = [
        row[4] for i, row in enumerate(data["data"]) if i > 0
    ]

    dataset.close()
