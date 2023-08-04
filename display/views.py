from django.shortcuts import render, redirect
from django.conf import settings

# Create your views here.
import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os
import textwrap
import math

def generate_final_df(merchant, category):
    # Load the cleaned dataset
    df = pd.read_csv(settings.CSV_FILE_PATH)

    # Filter the data based on user input
    walmart_df = df[df['merchant'] == merchant]
    walmart_df = walmart_df[walmart_df['Category_name'].str.contains(category, case=False, na=False)]

    Week_price_df = walmart_df.groupby(['name', 'Week']).agg({'Discount_price': 'mean', 'Impression': 'sum'}).reset_index()
    x_pivot = Week_price_df.pivot(index='Week', columns='name', values='Discount_price')
    x_values = pd.DataFrame(x_pivot.to_records())
    x_values.fillna(method='ffill', inplace=True)

    y_pivot = Week_price_df.pivot(index='Week', columns='name', values='Impression')
    y_values = pd.DataFrame(y_pivot.to_records())
    y_values.fillna(method='ffill', inplace=True)

    final_df = pd.DataFrame()
    for col in x_values.columns[1:]:
         #to store the results of the analysis for each column.
        results_values = {
        "name": [],
        "price_elasticity": [],
        "price_mean": [],
        "quantity_mean": [],
        "intercept": [],
        "t_score":[],
        "slope": [],
        "coefficient_pvalue" : [],
        "rsquared": [],
        }
        
        #to hold the data for the current column being processed.
        temp_df1 = pd.DataFrame()
        temp_df1['x'] = x_values[col]
        temp_df1['y'] = y_values[col]
        #Drops any rows with missing values in temp_df1
        temp_df1.dropna(inplace=True)
        x_value = temp_df1['x']
        y_value = temp_df1['y']
        X = sm.add_constant(x_value)
        #Constructs an Ordinary Least Squares (OLS) regression model using sm.OLS() from statsmodels, with     y_value as the dependent variable and x_value as the independent variable.
        model = sm.OLS(y_value, X)
        result = model.fit()

        #choose only those whose P-value is less than 5% errornous  (5% significance level)
        if result.f_pvalue < 0.05:

            rsquared = result.rsquared
            coefficient_pvalue = result.f_pvalue
            try:
                intercept,slope = result.params
            except:
                slope = result.params
            mean_price = np.mean(x_value)
            mean_quantity = np.mean(y_value)
            try:
                tintercept, t_score = result.tvalues
            except:
                pass
            
            #Price elasticity Formula
            price_elasticity = (slope)*(mean_price/mean_quantity)

                
                
            #Append results into dictionary for dataframe
            results_values["name"].append(col)
            results_values["price_elasticity"].append(price_elasticity)
            results_values["price_mean"].append(mean_price)
            results_values["quantity_mean"].append(mean_quantity)
            results_values["intercept"].append(intercept)
            results_values['t_score'].append(t_score)
            results_values["slope"].append(slope)
            results_values["coefficient_pvalue"].append(math.ceil(coefficient_pvalue * 1000) / 1000.0)
            results_values["rsquared"].append(rsquared)

            final_df = pd.concat([final_df,pd.DataFrame.from_dict(results_values)],axis=0,ignore_index=True)

    Name_Brand_Mapping = df[~df[['name', 'brand']].duplicated()][['name', 'brand']]
    final_df = final_df.merge(Name_Brand_Mapping, how='left', on='name')

    return final_df


# Available merchants and their corresponding categories
MERCHANTS_CATEGORIES = {
    'bhphotovideo.com': [
        'camera, mirrorless',
        'drive, storage, hard',
        'camera, shoot, point',
        'headphone, earbud, bluetooth',
        'tv, television, led',
        'camera, camcorder, action',
    ],
    'Walmart.com': [
        'tv, television, led',
        'car, gps, dash',
    ],
}


def input_view(request):
    merchants = MERCHANTS_CATEGORIES.keys()

    if request.method == 'POST':
        merchant = request.POST.get('merchant')
        category = request.POST.get('category')
        print('merchant:',merchant)
        print('category:',category)
               
        if merchant and category and merchant in MERCHANTS_CATEGORIES and category in MERCHANTS_CATEGORIES[merchant]:
            return redirect('results', merchant=merchant, category=category) 
        
        else:
            # If the form is submitted with invalid or missing options, return an error message or handle it as needed
            error_message = "Please select both a valid merchant and category."
            context = {
                'merchants': merchants,
                'MERCHANTS_CATEGORIES': MERCHANTS_CATEGORIES,
                'error_message': error_message,
            }
            print (context)
            return render(request, 'input.html', context)

    # If the form is not submitted or the input is invalid, display the form with available options.
    context = {
        'merchants': merchants,
        'MERCHANTS_CATEGORIES':MERCHANTS_CATEGORIES,
    }
    return render(request, 'input.html', context)

def view_chart(df):
    final_df = df.sort_values(by=['price_elasticity'])
    temp_df = final_df[['name', 'price_elasticity']]
    temp_df = temp_df[abs(temp_df['price_elasticity']) <= 50]
    plt.figure(figsize=(12, 10))
    ax = sns.barplot(x='price_elasticity', y='name', data=temp_df)
    ax.bar_label(ax.containers[0])
    plt.yticks(rotation=15)
    plt.subplots_adjust(left=0.2)
    max_label_length = 20
    wrap_length = 15
    y_labels = [textwrap.fill(label[:max_label_length], wrap_length) if len(label) > max_label_length else label for label in temp_df['name']]
    ax.set_yticklabels(y_labels)
    # plt.tight_layout()
    # Save the plot as an image
    plot_filename = 'plot.png'
    plot_path = os.path.join(settings.MEDIA_ROOT, plot_filename)
    os.makedirs(os.path.dirname(plot_path), exist_ok=True)
    plt.savefig(plot_path)
    
    # Close the plot to free up resources
    plt.close()
    
    # Return the path to the saved image
    return f'{settings.MEDIA_URL}{plot_filename}'




def result_view(request, merchant, category):
    final_df = generate_final_df(merchant, category)
    plot_url = view_chart(final_df)
    item_names = final_df['name'].unique()  # Get unique item names for the dropdown
    print('item_names:',item_names)
    selected_item = request.POST.get('item_name')  # Get the selected item from the form
    if selected_item and selected_item in item_names:
        selected_item_values = final_df[final_df['name'] == selected_item].reset_index().to_dict()
        print('selected_item_values:',selected_item_values)
        context = {
        'selected_merchant': merchant,
        'selected_category': category,       
        'plot_url': plot_url,
        'item_names': item_names,  # Pass the item names to the template
        'selected_item': selected_item,  # Pass the selected item to the template
        'selected_item_values': selected_item_values,  # Pass the selected item's data to the template
        # Other data to pass to the template...
        }
        return render(request, 'result.html', context)
    else:
        context = {
        'selected_merchant': merchant,
        'selected_category': category,       
        'plot_url': plot_url,
        'item_names': item_names,  # Pass the item names to the template
        'selected_item': selected_item,  # Pass the selected item to the template
        # 'selected_item_df': selected_item_df,  # Pass the selected item's data to the template
        # Other data to pass to the template...
        }
        return render(request, 'result.html', context)