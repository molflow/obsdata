from bs4 import BeautifulSoup
from datetime import datetime
import csv
import requests  # type: ignore

from obsdata.save_data import ObsData, Record


def set_request_data(
        dataset_id, site_id, parameter_id, time_interval, start_date, end_date):
    return {
        "agidse": 3 if time_interval == 'Annual' else 1,
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
            "AirFact.FactValue",
            "AirFact.Unc",
            "AirFact.StatusFlag",
            "AirFact.Flag1",
            "AirFact.Flag2",
            "AirFact.Flag3",
            "AirFact.Flag4",
            "AirFact.Flag5",
        ],
        "siidse": site_id,
        "paidse": parameter_id,
        "df": time_interval,
        "qscs": "load",
        "dttype": 1,
    }


def get_data(request_data):
    '''returns an instance of FedData where data are
       retrived from the
       Federal Land Manager Environmental Database
       http://views.cira.colostate.edu/fed/QueryWizard/
    '''
    request_url = "http://views.cira.colostate.edu/fed/Reports/RawDataReport2.aspx"  # noqa
    r = requests.post(request_url, data=request_data)
    soup = BeautifulSoup(r.content, 'html.parser')
    link = soup.find("a")
    href = link.get('href')
    url_base = "http://views.cira.colostate.edu"
    url_txt = url_base + href
    r_txt = requests.get(url_txt)
    return parse_fed_data(r_txt.text)


def status_flag_to_number(status_flag):
    return [
        "H1",  # Historical data that have not been assessed or validated
        "I0",  # Invalid value - unknown reason
        "I1",  # Invalid value - known reason
        "I2",  # noqa Invalid value (-999), though sample-level flag seems valid (SEM)
        "M1",  # Missing value because no value is available
        "M2",  # Missing value because invalidated by data originator
        "M3",  # Missing value due to clogged filter
        "NA",  # Not available from source data
        "V0",  # Valid value
        "V1",  # noqa Valid value but comprised wholly or partially of below detection limit data
        "V2",  # Valid estimated value
        "V3",  # Valid interpolated value
        "V4",  # noqa Valid value despite failing to meet some QC or statistical criteria
        "V5",  # Valid value but qualified because of possible contamination
        "V6",  # noqa Valid value but qualified due to non-standard sampling conditions
        "V7",  # noqa Valid value set equal to the detection limit (DL) since the value was below the DL
        "VM",  # Valid modeled value
        "VS",  # Valid substituted value
    ].index(status_flag)


def parse_fed_data(text):
    '''returns an instance of FedData
    '''

    def get_row_nr(rows, string):
        start_row_nr = [
            row_nr for row_nr, row in enumerate(rows) if row == string
        ][0] + 2
        end_row_nr = start_row_nr + [
            index for index, row in enumerate(rows[start_row_nr::]) if row == ''
        ][0]
        return (start_row_nr, end_row_nr)

    def get_data_dict(rows):
        datarows = list(csv.reader(rows, delimiter=';'))
        datadict = {}
        for column_nr in range(len(datarows[0])):
            datadict[datarows[0][column_nr]] = [
                row[column_nr] for index, row in enumerate(datarows)
                if index > 0
            ]
        return datadict

    def get_records(rows):
        records = []
        for row_nr, row in enumerate(csv.reader(rows, delimiter=';')):
            if row_nr == 0:
                date_index = row.index('Date')
                value_index = row.index('_Val')
                unc_index = row.index('_Unc')
                status_index = row.index('_StatusFlag')
            else:
                try:
                    date_i = datetime.strptime(
                        row[date_index], '%m/%d/%Y %H:%M:%S')
                except ValueError:
                    date_i = datetime.strptime(
                        row[date_index], '%m/%d/%Y')

                records.append(Record(
                    start_datetime=date_i,
                    end_datetime=-999,
                    value=float(row[value_index]),
                    uncertainty=float(row[unc_index]),
                    status=status_flag_to_number(row[status_index]),
                    status_flag=row[status_index],
                    nr_of_samples=-999
                ))
        return records

    rows = text.replace("\r", '').split("\n")

    data = {}
    for item in ["Datasets", "Sites", "Parameters", "Status Flags"]:
        (start_row_nr, end_row_nr) = get_row_nr(rows, item)
        data[item.lower()] = get_data_dict(
            rows[start_row_nr: end_row_nr])

    (start_row_nr, end_row_nr) = get_row_nr(rows, "Data")
    records = get_records(rows[start_row_nr: end_row_nr])

    return ObsData(
        data_version="",  # FIXME
        station_name=data["sites"]["Site"][0],
        station_code=data["sites"]["Code"][0],
        station_category="global",
        observation_category=(
            "Air sampling observation at a stationary platform"
        ),
        country_territory="",  # empty should be ok
        contributor=data["datasets"]["Dataset"][0].split(' ')[0].lower(),
        latitude=data["sites"]["Latitude"][0],
        longitude=data["sites"]["Longitude"][0],
        altitude=data["sites"]["Elevation"][0],
        nr_of_sampling_heights="1",
        sampling_heights="",  # empty should be ok
        contact_point="nmhyslop@ucdavis.edu",
        dataset=data["datasets"]["Dataset"][0],
        parameter=data["parameters"]["Parameter"][0],
        parameter_code=data["parameters"]["Code"][0],
        time_interval=data["datasets"]["Frequency"][0].lower(),
        measurement_unit=data["parameters"]["Units"][0].replace("Âµ", 'u'),
        measurement_method="",  # empty should be ok
        sampling_type="continuous",
        time_zone="UTC",
        measurement_scale="",  # empty should be ok
        status_flags=data["status flags"],
        records=records
    )
