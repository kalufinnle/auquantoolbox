import sys, os
parentPath = os.path.abspath("..")
if parentPath not in sys.path:
    sys.path.insert(0, parentPath)
import pandas as pd
import glob, json
import numpy as np
from dateutil import parser
from datetime import timedelta
from backtester.dataSource import data_source_classes
from backtester.dataSource.features_data_source import FeaturesDataSource
from backtester.modelLearningManagers.feature_manager import FeatureManager
from backtester.model_learning_system_parameters import ModelLearningSystemParamters
from backtester.modelLearningManagers.target_variable_manager import TargetVariableManager
from backtester.modelLearningManagers.feature_selection_manager import FeatureSelectionManager
from backtester.modelLearningManagers.feature_transformation_manager import FeatureTransformationManager
from backtester.modelLearningManagers.regression_model import RegressionModel
from backtester.modelLearningManagers.classification_model import ClassificationModel
from backtester.model_data import ModelData
from backtester.constants import *
from backtester.logger import *

class ModelLearningSystem:

    # This chunksize is different from chunkSize defined in mlsParams
    # This is useful to do training in chunks
    # NOTE: For now, do not use this chunkSize because feature transformation and model fit doesn't support chunks
    def __init__(self, mlsParams, chunkSize=None):
        self.mlsParams = mlsParams
        self.__instrumentIds = mlsParams.getInstrumentIds()
        self.__trainingDataSource = self.initializeDataSource(**mlsParams.getTrainingDataSourceParams())
        # self.__validationDataSource = self.initializeDataSource(**mlsParams.getValidationDataSourceParams())
        self.__testDataSource = self.initializeDataSource(**mlsParams.getTestDataSourceParams())
        self.__chunkSize = chunkSize
        self.__targetVariableManager = TargetVariableManager(mlsParams, instrumentIds=self.__instrumentIds, chunkSize=self.__chunkSize)
        self.__featureSelectionManager = FeatureSelectionManager(mlsParams)
        self.__featureTransformationManager = FeatureTransformationManager(mlsParams)
        # self.__trainingModelManager = RegressionModel(mlsParams)
        self.__trainingModelManager = ClassificationModel(mlsParams)

        # modelDict is the dictionary of models where keys are instrumentIds and
        # values are another dictionary with keys as targetVariableKey and value as ModelData
        self.__modelDict = {instrumentId : dict() for instrumentId in self.__instrumentIds}

    def initializeDataSource(self, **params):
        # TODO: Add **kwargs in all the dataSource classes to support variable number of arguments and cleanup this mess
        # or find some nice way to generalize the function arguments in the dataSource classes
        dataSourceClass = getattr(data_source_classes, params.pop('dataSourceName', DEFAULT_DATASOURCE))
        cachedFolderName = params.get('cachedFolderName', '')
        dataSetId = params.get('dataSetId', '')
        startDateStr = params.get('startDateStr', None)
        endDateStr = params.get('endDateStr', None)
        featureFolderName = params.pop('featureFolderName', 'features')
        dropFeatures = params.pop('dropFeatures', None)

        # NOTE: Hardcoded name of json file
        stockDataFileName = 'stock_data.json'
        stockDataFile = os.path.join(cachedFolderName, dataSetId, featureFolderName, stockDataFileName)
        actionDict = self.checkFeaturesExistence(stockDataFile, startDateStr, endDateStr)
        # TODO: Also compute and check the hash of instrument feature files with the hash stored in json file
        if actionDict['exist']:
            logInfo("Features found!")
        elif actionDict['recalculate']:
            dataSource = dataSourceClass(**params)
            featureManager = FeatureManager(self.mlsParams, dataSource, self.__instrumentIds, self.mlsParams.chunkSize,
                                            dropFeatures=dropFeatures, featureFolderName=featureFolderName, fingerprintFile=stockDataFileName)
            featureManager.computeInstrumentFeatures(self.__instrumentIds, writeFeatures=True)
        else:
            self.fixFeaturesData(dataSourceClass, actionDict, params.copy(), dropFeatures)

        if len(self.features) > 0:
            params['features'] = self.features # A list of column names
        else:
            params['features'] = None
        params['featureFolderName'] = featureFolderName
        return FeaturesDataSource(**params)

    def fixFeaturesData(self, dataSourceClass, actionDict, params, dropFeatures):
        startDateStr = params.get('startDateStr', None)
        endDateStr = params.get('endDateStr', None)
        for dates in actionDict['dateRange']:
            instrumentIds = [inst for inst in self.__instrumentIds if inst not in actionDict['instrumentIds']]
            params['instrumentIds'] = instrumentIds
            params['startDateStr'] = dates['startDate']
            params['endDateStr'] = dates['endDate']
            dataSource = dataSourceClass(**params)
            featureManager = FeatureManager(self,mlsParams, dataSource, instrumentIds, self.mlsParams.chunkSize, dropFeatures=dropFeatures)
            featureManager.computeInstrumentFeatures(instrumentIds, writeFeatures=True, prepend=dates['prepend'], updateFingerprint=True)

        if len(actionDict['instrumentIds']) > 0:
            params['instrumentIds'] = actionDict['instrumentIds']
            params['startDateStr'] = startDateStr
            params['endDateStr'] = endDateStr
            dataSource = dataSourceClass(**params)
            featureManager = FeatureManager(self.mlsParams, dataSource, actionDict['instrumentIds'], self.mlsParams.chunkSize, dropFeatures=dropFeatures)
            featureManager.computeInstrumentFeatures(actionDict['instrumentIds'], writeFeatures=True, updateFingerprint=True)

    def checkFeaturesExistence(self, stockDataFile, startDateStr, endDateStr):
        instrumentFeatureConfigs = self.mlsParams.getFeatureConfigsForInstrumentType(INSTRUMENT_TYPE_STOCK)
        self.features = list(map(lambda x: x.getFeatureKey(), instrumentFeatureConfigs))
        lookbackSize = FeatureManager.parseFeatureConfigs(instrumentFeatureConfigs)
        lookbackSize = lookbackSize if lookbackSize is None else lookbackSize - 1
        actionDict = {'exist' : False, 'recalculate' : True, 'instrumentIds' : [], 'dateRange' : []}
        try:
            with open(stockDataFile, 'r') as fp:
                fingerprint = json.load(fp)
        except FileNotFoundError:
            logWarn('stock_data.json file not found')
            return actionDict
        if lookbackSize != fingerprint['lookbackSize']:
            return actionDict
        if not set(self.features).issubset(set(fingerprint['features'])):
            return actionDict
        existingInstrumentFiles = glob.glob(os.path.join(os.path.dirname(stockDataFile), '*.csv'))
        existingInstruments = [os.path.splitext(os.path.basename(instrumentFile))[0] for instrumentFile in existingInstrumentFiles]
        actionDict['instrumentIds'] = list(np.setdiff1d(self.__instrumentIds,
                                           list(set(existingInstruments) & set(fingerprint['stocks']))))
        actionDict['recalculate'], actionDict['dateRange'] = self.checkFeaturesDates(fingerprint,
                                                                                     startDateStr, endDateStr)
        if len(actionDict['instrumentIds']) > 0 or len(actionDict['dateRange']) > 0 :
            return actionDict
        actionDict['exist'] = True
        actionDict['recalculate'] = False
        return actionDict

    def checkFeaturesDates(self, fingerprint, expStartDateStr, expEndDateStr):
        if expStartDateStr is None or expEndDateStr is None:
            raise ValueError
        expStartDate = parser.parse(expStartDateStr)
        expEndDate = parser.parse(expEndDateStr)
        orgStartDate = parser.parse(fingerprint['startDate'])
        orgEndDate = parser.parse(fingerprint['endDate'])
        periodStartDate = None if fingerprint['periodStartDate'] is None else parser.parse(fingerprint['periodStartDate'])
        periodEndDate = None if fingerprint['periodEndDate'] is None else parser.parse(fingerprint['periodEndDate'])
        cond1 = orgStartDate > expStartDate and orgEndDate < expEndDate
        cond2 = orgStartDate > expStartDate and orgEndDate >= expEndDate
        cond3 = orgStartDate <= expStartDate and orgEndDate < expEndDate
        cond4 = expStartDate > orgEndDate
        cond5 = expEndDate < orgStartDate
        topDateStr = (orgStartDate - timedelta(days=1)).strftime('%Y%m%d') if periodStartDate is None else fingerprint['periodStartDate']
        botDateStr = (orgEndDate + timedelta(days=1)).strftime('%Y%m%d') if periodEndDate is None else fingerprint['periodEndDate']
        if cond1:
            return False, [dict(startDate=expStartDateStr,
                                endDate=topDateStr,
                                prepend=True),
                           dict(startDate=botDateStr,
                                endDate=expEndDateStr,
                                prepend=False)]
        if (cond2 and cond5) or (cond3 and cond4):
            return True, [dict(startDate=expStartDateStr,
                               endDate=expEndDateStr,
                               prepend=False)]
        elif cond2:
            return False, [dict(startDate=expStartDateStr,
                                endDate=topDateStr,
                                prepend=True)]
        elif cond3:
            return False, [dict(startDate=botDateStr,
                                endDate=expEndDate.strftime('%Y%m%d'),
                                prepend=False)]
        else:
            return False, []

    def getInstrumentDataFileName(self, cachedFolderName, dataSetId, instrumentId):
        return os.path.join(cachedFolderName, dataSetId, instrumentId + '.csv')

    def getTrainingInstrurmentData(self, instrumentId):
        return self.__trainingDataSource.getInstrumentUpdates(instrumentId, self.__chunkSize)[instrumentId]

    def getTestInstrurmentData(self, instrumentId):
        return self.__testDataSource.getInstrumentUpdates(instrumentId, self.__chunkSize)[instrumentId]

    def getTargetVariables(self, targetVariableConfigs):
        targetVariableConfigs = targetVariableConfigs if isinstance(targetVariableConfigs, list) else [targetVariableConfigs]
        targetVariableKeys = map(lambda x: x.getFeatureKey(), targetVariableConfigs)
        targetVariable = {}
        for key in targetVariableKeys:
            targetVariable[key] = self.__targetVariableManager.getTargetVariableByKey(key)
        return targetVariable

    # Computes targetVariables of an instrument or reads from file
    # NOTE: 'dataParams' is required when 'useFile' is True
    def computeTargetVariables(self, instrumentData, instrumentId, targetVariableConfigs, useFile=False, dataParams=None, useTimeFrequency=True):
        targetVariableKeys = list(map(lambda x: x.getFeatureKey(), targetVariableConfigs))
        timeFrequency = instrumentData.getTimeFrequency() if useTimeFrequency else None
        if useFile:
            fileName = self.getInstrumentDataFileName(dataParams.get('cachedFolderName', ''), dataParams.get('dataSetId', ''), instrumentId)
            if dataParams.get('startDateStr', None) is None or dataParams.get('endDateStr', None) is None:
                dateRange = None
            else:
                dateRange = (dataParams.get('startDateStr'), dataParams.get('endDateStr'))
            self.__targetVariableManager.readTargetVariables(fileName, targetVariableKeys, dateRange=dateRange)
            return
        self.__targetVariableManager.computeTargetVariables(0, instrumentData.getBookData(), instrumentId,
                                                            targetVariableConfigs, timeFrequency)
        # TODO: Method to calculate targetVariables in chunk. Use the below code somewhere else
        # for chunkNumber, instrumentDataChunk in instrumentData.getBookDataChunk():
        #     self.__targetVariableManager.computeTargetVariables(chunkNumber, instrumentDataChunk, instrumentId,
        #                                                         targetVariableConfigs, timeFrequency)
        #     targetVariable = self.getTargetVariables(targetVariableConfigs)
        #     print(chunkNumber, targetVariable)
        # targetVariable = self.__targetVariableManager.getLeftoverTargetVariableChunk()
        # print(chunkNumber+1, targetVariable)

    def getFeatureSet(self):
        return self.mlsParams.features

    def findBestModel(self, instrumentId, useTargetVaribleFromFile=False, useTimeFrequency=True):
        # TODO: Some function arguments are hardcoded. Make it changeable
        instrumentData = self.getTrainingInstrurmentData(instrumentId)
        targetVariableConfigs = self.mlsParams.getTargetVariableConfigsForInstrumentType(INSTRUMENT_TYPE_STOCK)
        modelConfigs = self.mlsParams.getModelConfigsForInstrumentType(INSTRUMENT_TYPE_STOCK)
        self.computeTargetVariables(instrumentData, instrumentId, targetVariableConfigs,
                                    useFile=useTargetVaribleFromFile, dataParams=self.mlsParams.getTrainingDataSourceParams(),
                                    useTimeFrequency=useTimeFrequency)
        targetVariablesData = self.getTargetVariables(targetVariableConfigs)
        # print(targetVariablesData)
        self.__featureSelectionManager.pruneFeatures(instrumentData.getBookData(), targetVariablesData,
                                                     aggregationMethod='intersect')
        selectedFeatures = self.__featureSelectionManager.getAllSelectedFeatures()
        print("Selected Features for %s:" % instrumentId, selectedFeatures)
        for targetVariableConfig in targetVariableConfigs:
            key = targetVariableConfig.getFeatureKey()
            selectedInstrumentData = instrumentData.getBookData()[selectedFeatures[key]]
            self.__featureTransformationManager.transformFeatures(selectedInstrumentData)
            columns = selectedInstrumentData.columns
            transformedInstrumentData = pd.DataFrame(index=selectedInstrumentData.index, columns=columns)
            transformedInstrumentData[columns] = self.__featureTransformationManager.getTransformedData()
            # print(transformedInstrumentData[key])
            # self.__featureTransformationManager.writeTransformers('transformersss.pkl')
            self.__trainingModelManager.fitModel(transformedInstrumentData, targetVariablesData[key])
            self.__modelDict[instrumentId][key] = ModelData(instrumentId, targetVariableConfig, selectedFeatures[key],
                                                        self.__featureTransformationManager.getTransformers(),
                                                        self.__trainingModelManager.getModel())

            # print(self.__trainingModelManager.predict(transformedInstrumentData))

    def getFinalMetrics(self, instrumentId, dataHandler, dataParamsHandler, targetVariableConfigs, modelConfigDict, useTargetVaribleFromFile=False, useTimeFrequency=True):
        instrumentData = dataHandler(instrumentId)
        self.computeTargetVariables(instrumentData, instrumentId, targetVariableConfigs,
                                    useFile=useTargetVaribleFromFile, dataParams=dataParamsHandler(),
                                    useTimeFrequency=useTimeFrequency)
        targetVariablesData = self.getTargetVariables(targetVariableConfigs)
        # print(targetVariablesData)
        for targetVariableConfig in targetVariableConfigs:
            key = targetVariableConfig.getFeatureKey()
            modelData = self.__modelDict[instrumentId][key]
            if len(modelData.getModelFeatures()) > 0:
                selectedInstrumentData = instrumentData.getBookData()[modelData.getModelFeatures()]
            else:
                selectedInstrumentData = instrumentData.getBookData()
            self.__featureTransformationManager.transformFeaturesUsingTransformers(selectedInstrumentData, modelData.getModelTransformers())
            columns = selectedInstrumentData.columns
            transformedInstrumentData = pd.DataFrame(index=selectedInstrumentData.index, columns=columns)
            transformedInstrumentData[columns] = self.__featureTransformationManager.getTransformedData()
            for modelKey in modelData.getModels():
                print("=================================================================")
                print("Model Key:", modelKey, "| Stock:", instrumentId, '| targetVariable:', key)
                self.__trainingModelManager.addModel(modelData.getModelByModelKey(modelKey), modelKey)
                print(self.__trainingModelManager.evaluateModel(transformedInstrumentData, targetVariablesData[key],
                                                                modelConfig=modelConfigDict[modelKey]))
                print("=================================================================")

    def runModels(self):
        # TODO: Find a better way to infer whether to use target variable from file or not (maybe through config dict)
        useTargetVaribleFromFile = True
        useTimeFrequency = True
        targetVariableConfigs = self.mlsParams.getTargetVariableConfigsForInstrumentType(INSTRUMENT_TYPE_STOCK)
        modelConfigs = self.mlsParams.getModelConfigsForInstrumentType(INSTRUMENT_TYPE_STOCK)
        modelConfigDict = {config.getKey() : config for config in modelConfigs}
        for instrumentId in self.__instrumentIds:
            print("STOCK:", instrumentId)
            self.findBestModel(instrumentId, useTargetVaribleFromFile=useTargetVaribleFromFile, useTimeFrequency=useTimeFrequency)
            # print(self.__modelDict)
            print("Metrics on Training Data:")
            self.getFinalMetrics(instrumentId, self.getTrainingInstrurmentData, self.mlsParams.getTrainingDataSourceParams,
                                targetVariableConfigs, modelConfigDict, useTargetVaribleFromFile=useTargetVaribleFromFile, useTimeFrequency=useTimeFrequency)
            print("Metrics on Test Data:")
            self.getFinalMetrics(instrumentId, self.getTestInstrurmentData, self.mlsParams.getTestDataSourceParams,
                                targetVariableConfigs, modelConfigDict, useTargetVaribleFromFile=useTargetVaribleFromFile, useTimeFrequency=useTimeFrequency)

if __name__ == '__main__':
    instrumentIds = ['SIZ', 'MLQ']
    chunkSize = 1000
    mlsParams = ModelLearningSystemParamters(instrumentIds, chunkSize=chunkSize)
    system1 = ModelLearningSystem(mlsParams, chunkSize=None)
    system1.runModels()
