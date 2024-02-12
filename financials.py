import requests
from bs4 import BeautifulSoup as bs

#metrics needed to calculate the fair value
metric = ['Price', 'EPS next 5Y', 'Beta', 'Shs Outstand']

def fundamental_metric(soup,metric):
    '''
    Returns a value of a certain metric in a parsed website

            Parameters:
                    soup (BeautifulSoup object): parsed website
                    metric (str): desired metric

            Returns:
                    value (str): metric found in the website
    '''

    # the table which stores the data in Finviz has html table attribute class of 'snapshot-td2'
    return soup.find(text = metric).find_next(class_='snapshot-td2').text
   
def get_finviz_data(ticker):
    '''
    Returns a dictionary of metrics found in the ewbsite Finviz for a given company ticker

            Parameters:
                    ticker (str): A company ticker  

            Returns:
                    dict_finviz (dict): A dictionary containing the desired metrics 
    '''
    try:
        url = ("http://finviz.com/quote.ashx?t=" + ticker.lower())
        soup = bs(requests.get(url,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}).content,features="lxml")
        dict_finviz = {}        
        for m in metric:   
            dict_finviz[m] = fundamental_metric(soup,m)
        for key, value in dict_finviz.items():
            # replace percentages
            if (value[-1]=='%'):
                dict_finviz[key] = value[:-1]
                dict_finviz[key] = float(dict_finviz[key])
            # billion
            if (value[-1]=='B'):
                dict_finviz[key] = value[:-1]
                dict_finviz[key] = float(dict_finviz[key])*1000000000  
            # million
            if (value[-1]=='M'):
                dict_finviz[key] = value[:-1]
                dict_finviz[key] = float(dict_finviz[key])*1000000
            try:
                dict_finviz[key] = float(dict_finviz[key])
            except:
                pass    
    except Exception as e:
        print (e)
        print ('Not successful parsing ' + ticker + ' data.')      
    return dict_finviz

def discount_rate(finviz_data):
    '''
    Returns the dicount rate for a given value of beta

            Parameters:
                    finviz_data (dict): dictionary containing the beta value

            Returns:
                    discount_rate (float): the corresponding discount rate
    '''
    Beta = finviz_data['Beta']
    discount_rate = 7
    if type(Beta)==str:
        return None
    if(Beta<0.80):
        discount_rate = 5
    elif(Beta>=0.80 and Beta<1):
        discount_rate = 6
    elif(Beta>=1 and Beta<1.1):
        discount_rate = 6.5
    elif(Beta>=1.1 and Beta<1.2):
        discount_rate = 7
    elif(Beta>=1.2 and Beta<1.3):
        discount_rate =7.5
    elif(Beta>=1.3 and Beta<1.4):
        discount_rate = 8
    elif(Beta>=1.4 and Beta<1.6):
        discount_rate = 8.5
    elif(Beta>=1.61):
        discount_rate = 9   

    return discount_rate

def calculate_intrinsic_value(acao,EPS_growth_5Y, EPS_growth_6Y_to_10Y, EPS_growth_11Y_to_20Y, discount_rate,finviz_data):
    '''
    Returns the fair value of a company according to the DCF model

            Parameters:
                    acao (ticker object): target company
                    EPS_growth_5Y (float): percentage growth in the next 5Y
                    EPS_growth_6Y_to_10Y (float): percentage growth in the next 6 to 10Y
                    EPS_growth_11Y_to_20Y (float): percentage growth in the next 11 to 20Y
                    discount_rate (float): discount rate of the company's cashflows
                    finviz_data (dict): dictionary containing the metrics

            Returns:
                    intrinsic_value (float): the company's fair value
    '''   
    #get values
    FCF2=acao.cashflow.loc['Total Cash From Operating Activities']+acao.cashflow.loc['Capital Expenditures']
    cash_flow=FCF2[0]
    total_debt=acao.balancesheet.loc['Long Term Debt'][0]+acao.balancesheet.loc['Short Long Term Debt'][0]
    cash_and_ST_investments=acao.balancesheet.loc['Cash'][0]
    shares_outstanding=finviz_data['Shs Outstand']
    
    
    # Convert all percentages to decmials
    EPS_growth_5Y_d = EPS_growth_5Y/100
    EPS_growth_6Y_to_10Y_d = EPS_growth_6Y_to_10Y/100
    EPS_growth_11Y_to_20Y_d = EPS_growth_11Y_to_20Y/100
    discount_rate_d = discount_rate/100
    
    # Lists of projected cash flows from year 1 to year 20
    cash_flow_list = []
    cash_flow_discounted_list = []
    year_list = []
    
    
    # Years 1 to 5
    for year in range(1, 6):
        year_list.append(year)
        cash_flow*=(1 + EPS_growth_5Y_d)        
        cash_flow_list.append(cash_flow)
        cash_flow_discounted = cash_flow/((1 + discount_rate_d)**year)
        cash_flow_discounted_list.append(cash_flow_discounted)
    
    # Years 6 to 10
    for year in range(6, 11):
        year_list.append(year)
        cash_flow*=(1 + EPS_growth_6Y_to_10Y_d)
        cash_flow_list.append(cash_flow)
        cash_flow_discounted = cash_flow/((1 + discount_rate_d)**year)
        cash_flow_discounted_list.append(cash_flow_discounted)
    
    # Years 11 to 20
    for year in range(11, 21):
        year_list.append(year)
        cash_flow*=(1 + EPS_growth_11Y_to_20Y_d)
        cash_flow_list.append(cash_flow)
        cash_flow_discounted = cash_flow/((1 + discount_rate_d)**year)
        cash_flow_discounted_list.append(cash_flow_discounted)
    
    intrinsic_value = (sum(cash_flow_discounted_list) - total_debt + cash_and_ST_investments)/shares_outstanding

    return round(intrinsic_value,2)
