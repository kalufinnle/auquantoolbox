from backtester.timeRule.time_rule import TimeRule
from datetime import datetime, timedelta
import pandas as pd
from pandas.tseries.offsets import CustomBusinessHour
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import USFederalHolidayCalendar
import os


class USTimeRule(CustomTimeRule):
    def __init__(self, startDate, endDate, frequency='H', sample='1'):
        CustomTimeRule.__init__(startDate = startDate, endDate = endDate, calendar = USFederalHolidayCalendar(), frequency = frequency, sample = sample)
        
    #     self.__cachedFolderName = cachedFolderName
    #     self.__dataSetId = dataSetId
    #     self.__startDate = startDate
    #     self.__endDate = endDate
    #     acceptable_freq = ['D', 'M', 'H', 'S']
    #     if frequency not in acceptable_freq:
    #         raise ValueError('Frequency Value Not acceptable. Specify D, M, H, S')
    #     self.__frequency = frequency
    #
    # def createBusinessDaySeries(self):
    #     bday_us = CustomBusinessDay(calendar=USFederalHolidayCalendar())
    #     return pd.date_range(start=self.__startDate, end=self.__endDate, freq= bday_us)
    #
    # def createBusinessHourSeries(self):
    #     bhour_us = CustomBusinessHour(start='9:00', end='16:00', calendar=USFederalHolidayCalendar())
    #     return pd.date_range(start=self.__startDate, end=self.__endDate, freq= bhour_us)
    #
    # def createBusinessMinSeries(self):
    #     hour_series = createBusinessHourSeries()
    #     return pd.date_range(hour_series.min(), hour_series.max(), freq='min')
    #
    #
    # def createBusinessSecSeries(self):
    #     hour_series = createBusinessHourSeries()
    #     return pd.date_range(hour_series.min(), hour_series.max(), freq='s')
