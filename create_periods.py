from datetime import datetime
import calendar
import sys


if __name__ == "__main__":
    first_day = 5
    first_month = 3
    first_year = 2019

    end_day = 10
    end_month = 6
    end_year = 2019

    period_list = []

    for year in range(first_year, end_year + 1):
        for month in range (first_month, end_month+1):
            if month == first_month:
                start_day = first_day
            else:
                start_day = 1
            if month == end_month:
                stop_day = end_day
            else:
                _, stop_day = calendar.monthrange(year, month)
            # print(f'Период: год {year}, месяц {month}, первый день периода {start_day}, последний день периода {stop_day}')
            d = {'y':year, 'm':month, 'start_d':start_day, 'stop_d':stop_day}
            period_list.append(d)
    
    for d in period_list:
        y, m, start_d, stop_d = d.values()
        print(f'Период: год {y}, месяц {m}, первый день периода {start_d}, последний день периода {stop_d}')
            
            
