from requests import request, exceptions
from dotenv import dotenv_values
from argparse import ArgumentParser
from json import load
from time import sleep

config = dotenv_values(".env")
BUTTERCMS_BASE_URL = "https://api.buttercms.com/v2"

parser = ArgumentParser(
    prog="ButterCMS Migration",
    description="A utility script for migrating your content into ButterCMS"
)
parser.add_argument(
    '-u',
    '--update',
    help="Update either existing pages or collections on ButterCMS",
    choices=['pages', 'collection']
)
parser.add_argument(
    '-s',
    '--status',
    default="draft",
    help="Set status of the content being created on ButterCMS",
)
parser.add_argument(
    '-v',
    '--verbose',
    default=False,
    action='store_true',
    help="Instruct script to print output at every step along the way",
)
parser.add_argument(
   '-f',
   '--file',
   help="Specify the path to the data source file containing the migration data",
)
args = parser.parse_args()


class DataMigrator:
    def __init__(self, file_path):
        if args.verbose:
            print('Reading data from {0} input source'.format(file_path))

        file = open(file_path)
        data = load(file)

        if 'pages' not in data or 'collection' not in data:
            raise Exception("Input data from {0} does not contain pages or collection keys".format(file_path))

        self.content = data
        self.page_slugs = {"product_collections": [], "customer_reviews": []}

    @staticmethod
    def api_request(route, data, method="POST"):
        try:
            # print("ENDPOINT =>", "{0}/{1}".format(BUTTERCMS_BASE_URL, route))

            req = request(
                url="{0}/{1}".format(BUTTERCMS_BASE_URL, route),
                json=data,
                method=method,
                headers={"Authorization": "Token {0}".format(config['BUTTERCMS_WRITE_API_KEY'])}
            )

            return req

        except exceptions.HTTPError as error:
            raise Exception("Connection Error: {0}".format(error))

    def create_pages(self):
        for index, page in enumerate(self.content['pages']):
            page['status'] = args.status

            req = self.api_request('pages', page)

            if req.status_code in [200, 202]:
                self.page_slugs[page['type']].append(page['slug'])

                if args.verbose:
                    print("Created page {0} with slug: {1}".format(index, page['slug']))

        if args.verbose:
            print("{0} items processed".format(len(self.content['pages'])))

    def create_collection(self):
        self.create_pages()
        sleep(20)

        for item in self.content['collection']['fields'][0].values():
            item['product_collections'] = self.page_slugs['product_collections']
            item['customer_reviews'] = self.page_slugs['customer_reviews']

        self.content['collection']['status'] = args.status

        req = self.api_request('content/', self.content['collection'])

        # print(req.json())

        if req.status_code in [200, 202]:
            if args.verbose:
                print("Created collection with key: {0}".format(self.content['collection']['key']))

    def update_content(self):
        if args.update == "collection":
            collection = self.content['collection']

            req = self.api_request('content/{0}/'.format(collection['key']), collection, "PATCH")

            if req.status_code in [200, 202]:
                if args.verbose:
                    print("Updated collection with key: {0}".format(self.content['collection']['key']))
            return

        if args.update == "pages":
            for index, page in enumerate(self.content['pages']):
                page['status'] = args.status

                if args.verbose:
                    print("Updating content for slug: {0}".format(page['slug']))

                req = self.api_request(
                    'pages/*/{0}/'.format(page["slug"]),
                    page,
                    method="PATCH"
                )

                if req.status_code in [200, 202]:
                    print('Data updated')


Migrator = DataMigrator(args.file)

if args.update:
    Migrator.update_content()
else:
    Migrator.create_collection()
