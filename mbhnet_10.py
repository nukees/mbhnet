# Импорт базовых библиотек
from datetime import datetime
import sys

# Импорт подключаемых библиотек
import pandas as pd
import pyexcelerate as xls
import mysql.connector as db


def summa_spiska(x_list):
    sum = 0
    for x in x_list:
        sum = sum + x
    return sum


if __name__ == "__main__":
    ######################################
    # Изменять дату в файле variables.py #
    ######################################
    try:
        # Импорт переменных
        import variables

        year = variables.year
        month = variables.month
        day_start = variables.day_start
        day_end = variables.day_end
    except:
        print("Отсутствует файл с переменными, или он переменные заданы некорректно ")
        sys.exit()
    ###################################
    

    # Код основной программы
    if not (isinstance(year,int) and isinstance(month,int) and isinstance(day_start,int) and isinstance(day_end,int)):
        print('Некорректно указаны переменные год/месяц/дата')
        input()
        sys.exit()

    try:
        db_connection = db.connect(host='10.245.41.196', port='3306',user='soctraf', password='traffic', database='traf')
        if db_connection.is_connected():
            print('Успешное подключение к БД.')
            print('Successful connection to the DB.')
            print('')
    except:
        e = sys.exc_info()
        print(f'Ошибка подключения к БД  - {e}. \n')
        print(f'Error connecting to the DB - {e}. \n')
        print('')
        input()
        sys.exit()
    
    # Запрос к БД на выборку 10Гб интерфейсов
    sql_string = """
    SELECT
    bd.nameds as 'Interface',
    round(bd.peak/(1000*100000), 2) as 'Percent',
    round(bd.peak, 2) as 'Speed',
    bd.day as 'Day',
    bd.month as 'Month'
    FROM mbh_day as bd
    WHERE
    bd.peak > 7500000000 AND
    (bd.nameds like "%csg%" OR bd.nameds like "%pagg%") AND
    (
	bd.nameds like "%|Te%" OR 
	bd.nameds like "%|xe%" OR
	bd.nameds like "%:te%" OR
 	bd.nameds like "%:xe%"
	) AND
    bd.nameds not like "%Po1%" AND
    bd.nameds not like "%Po2%" AND
    bd.nameds not like "%Bundle%" AND
    bd.year = {} AND
    bd.month = {} AND
    bd.day >= {} AND
    bd.day <= {}
    order by
    bd.nameds,
    bd.month,
    bd.day
    """.format(year, month, day_start, day_end)
    
    df = pd.read_sql(sql_string, db_connection)
    db_connection.close()

    k = 5 #Сколько дней подряд

    list_date = df['Day'].tolist()

    start = list_date[0]
    
    if (list_date[1]-list_date[0]) == 1:
        list_date_bool = [1]
    else:
        list_date_bool = [0]

    for i in range (1, len(list_date)):
        if (list_date[i]-start) == 1:
            start = list_date[i]

            list_date_bool.append(1)
        else:
            start = list_date[i]
            list_date_bool.append(0)

    delta = 0
    w_list = []

    for i in range (0, len(list_date_bool)):
        if (i+k) > len(list_date_bool):
            delta = delta + 1
        if summa_spiska(list_date_bool[i-delta:i+k-delta]) == k:
            w_list.append(1)
        else:
            w_list.append(0)
    

    z_count = 0
    step = k-1
    for i in range (0, len(w_list)):
        if w_list[i] == 1 and z_count == 0:
            # print('z=1 and count=0')
            z_count = 1
            step = k-1
        if w_list[i] == 0 and z_count == 1:
            # print('?')
            w_list[i] = 1
            step = step - 1
            if step == 0:
                z_count = 0
            
    # В базовую таблицу добавляем столбец "Check", который указывает, что дни идут подряд (1-день подряд, 0-день не подряд).        
    df['Check'] = pd.DataFrame(w_list)
    df.to_clipboard(index=False)

    # Из таблицы отбираем только значения Check = 1
    df_selected = df[df['Check'] == 1]
    #df - содержит изначальные данные + столбец Check, который отобржает дни подряд
    #df_selected - содержит данные только с днями подряд
    #x_total - содержит отсортированные и обработанные данные

    #Группириуем по интерфейсам (преобразовывается в тип Pandas Series)
    y_left = df_selected.groupby(['Interface']).size()
    # Складываем суммарную скорость сгруппированных интерфейсов (преобразовывается в тип Pandas Series)
    y_right = df_selected.groupby(['Interface'])['Speed'].sum()
    
    # Преобразовываем полученные pandas.series в pandas.df
    x_left = y_left.to_frame()
    x_right = y_right.to_frame()
    # Формируем результирующую таблицу
    x_total = pd.merge(x_left, x_right, how='inner', left_on='Interface', right_on='Interface', )
    x_total['speed_int'] = x_total['Speed']/x_total[0]
    x_total['Average daily utilization, %'] = x_total['speed_int']/100000000
    x_total = x_total.round(2)

    # Переименовываем столбцы для красоты при размещении в excel файл
    df.rename(columns={'Percent': 'Daily utilization, %', 'Speed': 'Daily utilization, b/s'}, inplace=True)
    x_total.reset_index(inplace=True)
    x_total.rename(columns={0: 'Days in a row', 'Speed': 'Total utilization for selected days, b/s', 'speed_int': 'Average daily utilization, b/s'}, inplace=True)
        
    # В excel файл выводим таблицу df в второй лист (Extended data), и обработанные данные x_total в первый лист(Calculated data)
    
    file_name = "OUT\\{}_{}_{}-mbh_10Gb.xlsx".format(year, month, day_end)
    wb = xls.Workbook()

    data = [x_total.columns.tolist(), ] + x_total.values.tolist()
    ws1 = wb.new_sheet('Calculated data', data=data)
    ws1.set_row_style(1, xls.Style(alignment = xls.Alignment(horizontal = 'center'), font = xls.Font(bold=True)))
    ws1.set_col_style(1, xls.Style(size=-1))
    ws1.set_col_style(2, xls.Style(size=-1))
    ws1.set_col_style(3, xls.Style(size=0))
    ws1.set_col_style(4, xls.Style(size=27))
    ws1.set_col_style(5, xls.Style(size=27))

    data_1 = [df.columns.tolist(), ] + df.values.tolist()
    ws = wb.new_sheet('Extended data', data=data_1)
    ws.set_row_style(1, xls.Style(alignment = xls.Alignment(horizontal = 'center'), font = xls.Font(bold=True)))
    # ws.set_row_style(1, xls.Style(font = xls.Font(bold=True)))
    # Style(fill=Fill(background=Color(255,0,0,0))))
    # ws.set_cell_style(1, 1, Style(font=Font(bold=True), format=Format('mm/dd/yy')))
    ws.set_col_style(1, xls.Style(size=-1))
    ws.set_col_style(2, xls.Style(size=-1))
    ws.set_col_style(3, xls.Style(size=-1))
    ws.set_col_style(4, xls.Style(size=7))
    ws.set_col_style(5, xls.Style(size=7))
    ws.set_col_style(6, xls.Style(size=7))

    try:
        wb.save(file_name)
        print('Скрипт отработал успешно')
        print('The script worked successfully')
    except:
        print('Файл с таким именем открыт. Закройте файл и перезапустите скрипт.')
        print('A file with the same name is open. Close the file and restart the script.')
        print('')
    

