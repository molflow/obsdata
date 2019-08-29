import requests
from bs4 import BeautifulSoup
import csv


def create_site_file(dataset_id, dataset_name):

    url = "http://views.cira.colostate.edu/fed/Reports/DatasetDetail.aspx?dssl=1&dsidse={}".format(dataset_id)  # noqa
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    site_infos = [[
        "SiteID",
        "SiteCode",
        "SiteName",
        "CT",
        "ST",
        "EPACode",
        "Lat",
        "Lon",
        "Elev",
        "Start",
        "End"
    ]]

    table = soup.find('table', id="xplSite")

    for row in table.find_all('tr'):
        try:
            site_id = str(row).split("value=")[1].split("/")[0].replace('"', '')  # noqa
        except IndexError:
            continue
        site_info = [site_id]
        for info in row.find_all('td'):
            if not info.text == '':
                site_info.append(info.text)
        if not site_info == []:
            site_infos.append(site_info)

    outfile = "/tmp/fedsites_{}.csv".format(dataset_name)
    with open(outfile, mode='w') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',')
        for row in site_infos:
            csv_writer.writerow(row)


if __name__ == "__main__":

    dataset_names = ["castnet", "improve_aerosol"]
    dataset_ids = [23005, 10001]

    for id, name in zip(dataset_ids, dataset_names):

        create_site_file(id, name)
