#! /usr/bin/env python3
import argparse
import json
import logging
import logging.config
import os
import sys
import time
import re
from concurrent import futures
from datetime import datetime
import pandas as pd
import numpy as np
from fbprophet import Prophet
import json
import math

# Add Generated folder to module path.
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'generated'))

import ServerSideExtension_pb2 as SSE
import grpc
from ssedata import FunctionType
from scripteval import ScriptEval

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class ExtensionService(SSE.ConnectorServicer):
    """
    A simple SSE-plugin created for the HelloWorld example.
    """

    def __init__(self, funcdef_file):
        """
        Class initializer.
        :param funcdef_file: a function definition JSON file
        """
        self._function_definitions = funcdef_file
        self.ScriptEval = ScriptEval()
        os.makedirs('logs', exist_ok=True)
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logger.config')
        logging.config.fileConfig(log_file)
        logging.info('Logging enabled')

    @property
    def function_definitions(self):
        """
        :return: json file with function definitions
        """
        return self._function_definitions

    @property
    def functions(self):
        """
        :return: Mapping of function id and implementation
        """
        return {
            0: '_prophet',
            1: '_prophetScript'
        }

    @staticmethod
    def _get_function_id(context):
        """
        Retrieve function id from header.
        :param context: context
        :return: function id
        """
        metadata = dict(context.invocation_metadata())
        header = SSE.FunctionRequestHeader()
        header.ParseFromString(metadata['qlik-functionrequestheader-bin'])

        return header.functionId

    """
    Implementation of added functions.
    """

    @staticmethod
    def _prophetScript(request, context):
        """
        Mirrors the input and sends back the same data.
        :param request: iterable sequence of bundled rows
        :return: the same iterable sequence as received
        """

        # instantiate a list for measure data
        dateStampList = []
        figuresList = []
        forecastPeriods = None
        forecastType = None
        m = None
        yhat = None
        changePoint = None
        minFloor = None
        maxCap = None
        
        for request_rows in request:
            
            # iterate over each request row (contains rows, duals, numData)

            # pull duals from each row, and the numData from duals
            for row in request_rows.rows:
                # the first numData contains the date stamps
                dateStamps = [d.numData for d in row.duals][0]
                pythonDate = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(dateStamps) - 2)
                dateStampList.append(pythonDate)

                # the second numData contains the figures
                figures = int([d.numData for d in row.duals][1])
                figuresList.append(figures)
                
                # this is redundant and is the same in every row
                if not forecastPeriods:
                    forecastPeriods = int([d.numData for d in row.duals][2])
                if not forecastType:
                    forecastType = [d.strData for d in row.duals][3]
                if not yhat:
                    yhat = [d.strData for d in row.duals][6]
                if not changePoint:
                    changePoint = int([d.numData for d in row.duals][7])
                if not minFloor:
                    minFloor = int([d.numData for d in row.duals][8])   
                if not maxCap:
                    maxCap = int([d.numData for d in row.duals][9])                                       

         # create data frame
        dataFrame = pd.DataFrame({'ds': dateStampList,'y': figuresList})
        print(dataFrame)
        if forecastType == 'hourly':
            # fit data to prophet
            m = Prophet(changepoint_prior_scale=changePoint)
            m.fit(dataFrame)
            
            #create future dataframe
            future = m.make_future_dataframe(periods=forecastPeriods, freq='H')
        
        if forecastType == 'daily':
            # fit data to prophet
            m = Prophet(changepoint_prior_scale=changePoint)
            m.fit(dataFrame)

            #create future dataframe
            future = m.make_future_dataframe(periods=forecastPeriods)
        
        if forecastType == 'monthly':
            # fit data to prophet
            
            m = Prophet(weekly_seasonality=False, changepoint_prior_scale=changePoint)
            m.add_seasonality(name='monthly', period=30.5, fourier_order=5)
            m.fit(dataFrame)
            
            #create future dataframe
            future = m.make_future_dataframe(periods=forecastPeriods, freq='MS')

        #create forecast and create a list
        if not m:
            # fit data to prophet
            
            m = Prophet(weekly_seasonality=False, changepoint_prior_scale=changePoint)
            m.add_seasonality(name='monthly', period=30.5, fourier_order=5)
            m.fit(dataFrame)

        forecast = m.predict(future)                  
        forecastList = forecast[yhat].values.tolist()
        dateList = pd.to_datetime(forecast['ds'].values.tolist())

        #convert forecast results to ints
        resultsList = []
        for val in forecastList:
            try:
                resultsList.append(int(val))
            except:
                resultsList.append(0)    
        
        finalDateList = []
        for ds in dateList:
            try:
                finalDateList.append(str(ds))
            except:
                finalDateList.append(0)        
        
        # Create an iterable of dual with the result
        dualsList = []
        dualsList.append([SSE.Dual(numData=d) for d in resultsList])
        dualsList.append([SSE.Dual(strData=d) for d in finalDateList])
        
        #create response rows
        response_rows = []
        for i in range(len(resultsList)):
            duals = [dualsList[z][i] for z in range(len(dualsList))]
            response_rows.append(SSE.Row(duals=iter(duals)))
        
        #set and send table header
        table = SSE.TableDescription(name='ProphetForecast')
        table.fields.add(dataType=SSE.NUMERIC)
        table.fields.add(dataType=SSE.STRING)
        md = (('qlik-tabledescription-bin', table.SerializeToString()),)
        context.send_initial_metadata(md)

        yield SSE.BundledRows(rows=response_rows)

    @staticmethod
    def _prophet(request, context):
        """
        Mirrors the input and sends back the same data.
        :param request: iterable sequence of bundled rows
        :return: the same iterable sequence as received
        """

        # instantiate a list for measure data
        dateStampList = []
        figuresList = []
        forecastPeriods = None
        outliers = None
        forecastType = None
        adjustments = None
        forecastReturnType = None
        changePoint = None
        fourierOrder = None
        m = None
        holidays = None
        
        for request_rows in request:
            # iterate over each request row (contains rows, duals, numData)
            # pull duals from each row, and the numData from duals
            for row in request_rows.rows:
                # this is redundant and is the same in every row
                if not adjustments:
                    adjustments = [d.strData for d in row.duals][0]
                
                if not changePoint:
                    tmpChangePoint = [d.numData for d in row.duals][1]
                    if math.isnan(tmpChangePoint):
                        changePoint = 0.05
                    else:
                        changePoint = tmpChangePoint                    
                
                # the first numData contains the date stamps
                dateStamp = [d.numData for d in row.duals][2]
                try: 
                    pythonDate = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(dateStamp) - 2)
                    dateStampList.append(pythonDate)
                except ValueError:
                    dateStampList.append(dateStamp)

                # the second numData contains the figures
                figures = int([d.numData for d in row.duals][3])
                figuresList.append(figures)

                if not forecastType:
                    forecastType = [d.strData for d in row.duals][4]                

                if not forecastPeriods:
                    forecastPeriods = int([d.numData for d in row.duals][5])

                if not forecastReturnType:
                    forecastReturnType = [d.strData for d in row.duals][6]

                if not fourierOrder:
                    tmpFourierOrder = [d.numData for d in row.duals][7]
                    if math.isnan(tmpFourierOrder):
                        fourierOrder = 5
                    else:
                        fourierOrder = int(tmpFourierOrder)  
                if not holidays:
                    holidays = [d.strData for d in row.duals][8]  

                if not outliers:
                    outliers = [d.strData for d in row.duals][9]



                                                                                               
        # create data frame
        dataFrame = pd.DataFrame({'ds': dateStampList,'y': figuresList})
        print(dataFrame)

        # Store the original indexes for re-ordering output later
        index = dataFrame.copy()

        # remove null values from df
        dataFrame = dataFrame.dropna()
        
        # Sort the Request Data Frame based on dates, as Qlik may send unordered data
        dataFrame = dataFrame.sort_values('ds')
        
        # drop extra periods from data frame
        dataFrame = dataFrame[:-forecastPeriods]
        maxDate = max(dataFrame['ds'])
        
        # remove outliers
        if len(outliers) > 2:
            outliersList = outliers.split(",")
            for outlier in outliersList:
                dataFrame.loc[dataFrame['ds'] == outlier,'y'] = None

        # create holidays
        if len(holidays) > 2:
            holidays_list = holidays.split(',')
            holidays_df = pd.DataFrame({
              'holiday': 'holiday',
              'ds': pd.to_datetime(holidays_list)
            })        
        
        if forecastType == 'hourly':
            # fit data to prophet
            if len(holidays) > 2:
                m = Prophet(changepoint_prior_scale=changePoint, holidays=holidays_df)
            else:
                m = Prophet(changepoint_prior_scale=changePoint)  
            m.fit(dataFrame)
            
            #create future dataframe
            future = m.make_future_dataframe(periods=forecastPeriods, freq='H')
        
        if forecastType == 'daily':
            # fit data to prophet
            if len(holidays) > 2:
                m = Prophet(changepoint_prior_scale=changePoint, holidays=holidays_df)
            else:
                m = Prophet(changepoint_prior_scale=changePoint)            
            m.add_seasonality(name='daily', period=1, fourier_order=fourierOrder)
            m.fit(dataFrame)

            #create future dataframe
            future = m.make_future_dataframe(periods=forecastPeriods)

        if forecastType == 'weekly':
            if len(holidays) > 2:
                m = Prophet(weekly_seasonality=True, changepoint_prior_scale=changePoint, holidays=holidays_df)
            else:
                m = Prophet(weekly_seasonality=True, changepoint_prior_scale=changePoint)
            m.add_seasonality(name='weekly', period=7, fourier_order=fourierOrder)
            m.fit(dataFrame)   
            future = m.make_future_dataframe(periods=forecastPeriods, freq='W')
        
        if forecastType == 'monthly':
            # fit data to prophet
            if len(holidays) > 2:
                m = Prophet(weekly_seasonality=False, changepoint_prior_scale=changePoint, holidays=holidays_df)
            else:
                m = Prophet(weekly_seasonality=False, changepoint_prior_scale=changePoint)  
            m.add_seasonality(name='yearly', period=365.25, fourier_order=fourierOrder)
            m.fit(dataFrame)
            
            #create future dataframe
            future = m.make_future_dataframe(periods=forecastPeriods, freq='MS')

        if not m:
            # fit data to prophet
            if len(holidays) > 2:
                m = Prophet(seasonality_mode='multiplicative', holidays=holidays_df)
            else:
                m = Prophet(seasonality_mode='multiplicative')  
            m.fit(dataFrame)
        
        #create forecast
        forecast = m.predict(future)

        #loop through adjustments for each time period and change yhat
        try:
            adjJson = json.loads(adjustments)
            for i in range(len(forecast)):
                for item in adjJson:
                    dt = datetime.strptime(item['firstField'], '%Y-%m-%d')
                    if dt == forecast.at[i, 'ds']:
                        adjustmentString = item["adjustment"].replace("m", "000000").replace("M", "000000").replace("k", "0000").replace("K", "0000")
                        if "%" in adjustmentString:
                            adjustmentPercent = float(adjustmentString.replace("%", ""))/100 + 1
                            forecast.at[i, forecastReturnType] = float(forecast.at[i,forecastReturnType]) * adjustmentPercent
                        else:    
                            forecast.at[i, forecastReturnType] = float(forecast.at[i,forecastReturnType]) + float(adjustmentString)
        except:
            print('No adjustments!') 
         
        #drop index column from data frame
        #dataFrame.drop(columns=['index'], inplace=True)

        # keep only the needed columns from the forecast
        forecast = forecast[['ds', forecastReturnType]]
        print(forecast)

        # merge two dataframes
        index = index.merge(forecast, on='ds', how='left')
        print(index)
        index['y'] = index.apply(lambda row: row[forecastReturnType] if row['ds'] > maxDate else row['y'], axis=1)
        #forecast['result'] = forecast.apply(lambda row: row[forecastReturnType] if row['y'] == 0 else row['y'], axis=1)

        forecastList = index['y'].values.tolist()

        #convert forecast results to ints
        resultsList = []
        for i, val in enumerate(forecastList):
            try:
                resultsList.append(int(val))
            except:
                resultsList.append(0)    

        # Create an iterable of dual with the result
        duals = iter([[SSE.Dual(numData=d)] for d in resultsList])

        # Yield the row data as bundled rows
        yield SSE.BundledRows(rows=[SSE.Row(duals=d) for d in duals])

        

    def GetCapabilities(self, request, context):
        """
        Get capabilities.
        Note that either request or context is used in the implementation of this method, but still added as
        parameters. The reason is that gRPC always sends both when making a function call and therefore we must include
        them to avoid error messages regarding too many parameters provided from the client.
        :param request: the request, not used in this method.
        :param context: the context, not used in this method.
        :return: the capabilities.
        """
        logging.info('GetCapabilities')
        # Create an instance of the Capabilities grpc message
        # Enable(or disable) script evaluation
        # Set values for pluginIdentifier and pluginVersion
        capabilities = SSE.Capabilities(allowScript=True,
                                        pluginIdentifier='Prophet',
                                        pluginVersion='v1.1.0')

        # If user defined functions supported, add the definitions to the message
        with open(self.function_definitions) as json_file:
            # Iterate over each function definition and add data to the capabilities grpc message
            for definition in json.load(json_file)['Functions']:
                function = capabilities.functions.add()
                function.name = definition['Name']
                function.functionId = definition['Id']
                function.functionType = definition['Type']
                function.returnType = definition['ReturnType']

                # Retrieve name and type of each parameter
                for param_name, param_type in sorted(definition['Params'].items()):
                    function.params.add(name=param_name, dataType=param_type)

                logging.info('Adding to capabilities: {}({})'.format(function.name,[p.name for p in function.params]))

        return capabilities

    def ExecuteFunction(self, request_iterator, context):
        """
        Execute function call.
        :param request_iterator: an iterable sequence of Row.
        :param context: the context.
        :return: an iterable sequence of Row.
        """
        # Retrieve function id
        func_id = self._get_function_id(context)

        # Call corresponding function
        logging.info('ExecuteFunction (functionId: {})'.format(func_id))

        return getattr(self, self.functions[func_id])(request_iterator, context)

    def EvaluateScript(self, request, context):
        """
        This plugin provides functionality only for script calls with no parameters and tensor script calls.
        :param request:
        :param context:
        :return:
        """
        # Parse header for script request
        metadata = dict(context.invocation_metadata())
        header = SSE.ScriptRequestHeader()
        header.ParseFromString(metadata['qlik-scriptrequestheader-bin'])

        # Retrieve function type
        func_type = self.ScriptEval.get_func_type(header)

        # Verify function type
        if (func_type == FunctionType.Aggregation) or (func_type == FunctionType.Tensor):
            return self.ScriptEval.EvaluateScript(header, request, context, func_type)
        else:
            # This plugin does not support other function types than aggregation  and tensor.
            # Make sure the error handling, including logging, works as intended in the client
            msg = 'Function type {} is not supported in this plugin.'.format(func_type.name)
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details(msg)
            # Raise error on the plugin-side
            raise grpc.RpcError(grpc.StatusCode.UNIMPLEMENTED, msg)

    """
    Implementation of the Server connecting to gRPC.
    """

    def Serve(self, port, pem_dir):
        """
        Sets up the gRPC Server with insecure connection on port
        :param port: port to listen on.
        :param pem_dir: Directory including certificates
        :return: None
        """
        # Create gRPC server
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        SSE.add_ConnectorServicer_to_server(self, server)

        if pem_dir:
            # Secure connection
            with open(os.path.join(pem_dir, 'sse_server_key.pem'), 'rb') as f:
                private_key = f.read()
            with open(os.path.join(pem_dir, 'sse_server_cert.pem'), 'rb') as f:
                cert_chain = f.read()
            with open(os.path.join(pem_dir, 'root_cert.pem'), 'rb') as f:
                root_cert = f.read()
            credentials = grpc.ssl_server_credentials([(private_key, cert_chain)], root_cert, True)
            server.add_secure_port('[::]:{}'.format(port), credentials)
            logging.info('*** Running server in secure mode on port: {} ***'.format(port))
        else:
            # Insecure connection
            server.add_insecure_port('[::]:{}'.format(port))
            logging.info('*** Running server in insecure mode on port: {} ***'.format(port))

        # Start gRPC server
        server.start()
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            server.stop(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', nargs='?', default='50066')
    parser.add_argument('--pem_dir', nargs='?')
    parser.add_argument('--definition_file', nargs='?', default='../functions.json')
    args = parser.parse_args()

    # need to locate the file when script is called from outside it's location dir.
    def_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.definition_file)

    calc = ExtensionService(def_file)
    calc.Serve(args.port, args.pem_dir)
