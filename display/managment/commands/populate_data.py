import json
from django.core.management.base import BaseCommand
from display.models import Product

class Command(BaseCommand):
    help = 'Populate the Product table with data from a JSON file.'

    def handle(self, *args, **kwargs):
        with open('path/to/your/json/file.json') as json_file:
            data = json.load(json_file)
            for item in data:
                Product.objects.create(
                    name=item['name'],
                    price_elasticity=item['price_elasticity'],
                    price_mean=item['price_mean'],
                    quantity_mean=item['quantity_mean'],
                    intercept=item['intercept'],
                    t_score=item['t_score'],
                    slope=item['slope'],
                    coefficient_pvalue=item['coefficient_pvalue'],
                    rsquared=item['rsquared'],
                    brand=item['brand']
                )
        self.stdout.write(self.style.SUCCESS('Data successfully populated.'))