import numpy as np
import sys, os
sys.path.append(os.path.abspath(''))
from backtester.features.bollinger_bands_lower_feature import BollingerBandsLowerFeature
from backtester.instruments_manager import *
from backtester.instruments_lookback_data import *
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock,MagicMock
from initialize import Initialize
import math
import pandas as pd
import pytest

@pytest.fixture
def mockInstrumentManager():
    return Mock(spec=InstrumentManager)

@pytest.fixture
def mockInstrumentLookbackData():
	return Mock(spec=InstrumentsLookbackData)

def test_bollinger_bands_lower( mockInstrumentManager, mockInstrumentLookbackData):
    for i in range(1,4):
        k = Initialize()
        dataSet = k.getDataSet(i)
        mockInstrumentManager.getLookbackInstrumentFeatures.return_value = mockInstrumentLookbackData
        mockInstrumentLookbackData.getFeatureDf.return_value=dataSet["data"]
        resultInstrument = BollingerBandsLowerFeature.computeForInstrument(i, "", dataSet["featureParams"], "ma_m",  mockInstrumentManager)
        mockInstrumentManager.getDataDf.return_value = dataSet["data"]
        resultMarket = BollingerBandsLowerFeature.computeForMarket(i, "", dataSet["featureParams"], "ma_m", {},  mockInstrumentManager)
        assert round(resultMarket,2) == round(dataSet['bblf'][-1],2)
        assert round(resultInstrument['open'],2) == round(dataSet['bblf'][-1],2)
    for i in range(4,5):
        k = Initialize()
        dataSet = k.getDataSet(i)
        mockInstrumentManager.getLookbackInstrumentFeatures.return_value = mockInstrumentLookbackData
        mockInstrumentLookbackData.getFeatureDf.return_value=dataSet["data"]
        with pytest.raises(ValueError):
        	BollingerBandsLowerFeature.computeForInstrument(i, "", dataSet["featureParams"], "ma_m",  mockInstrumentManager)
        mockInstrumentManager.getDataDf.return_value = dataSet["data"]
        with pytest.raises(ValueError):
        	BollingerBandsLowerFeature.computeForMarket(i, "", dataSet["featureParams"], "ma_m", {},  mockInstrumentManager)
    for i in range(5,6):
        k = Initialize()
        dataSet = k.getDataSet(i)
        mockInstrumentManager.getLookbackInstrumentFeatures.return_value = mockInstrumentLookbackData
        mockInstrumentLookbackData.getFeatureDf.return_value=dataSet["data"]
        with pytest.raises(ValueError):
        	BollingerBandsLowerFeature.computeForInstrument(i, "", dataSet["featureParams"], "ma_m",  mockInstrumentManager)
        mockInstrumentManager.getDataDf.return_value = dataSet["data"]
        with pytest.raises(ValueError):
        	BollingerBandsLowerFeature.computeForMarket(i, "", dataSet["featureParams"], "ma_m", {},  mockInstrumentManager)
