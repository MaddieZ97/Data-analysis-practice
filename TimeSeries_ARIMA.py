import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# set figure size
from matplotlib.pylab import rcParams
rcParams['figure.figsize'] = 15, 6

# set ignore warnings
import warnings
warnings.filterwarnings('ignore')

# ARIMA model
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima_model import ARIMA
from statsmodels.tsa.stattools import acf, pacf


# import data
air_passengers = pd.read_csv("./AirPassengers.csv", header = 0,
                             parse_dates = [0],
                             names = ['Month', 'Passengers'],
                             index_col = 0)
air_passengers.head()
# note here we are using month as index


# 1. First examine the overall trend
air_passengers.plot(legend = True, title = 'Passengers over months')
plt.show()
# or
# plt.plot(air_passengers.index, air_passengers.Passengers)
# plt.title('Passengers over months')
# plt.show()

# Autocorrelation Function Plot
# if try plotting acf now
t = acf(air_passengers.Passengers)
plt.bar(x = range(len(t)), height = t )
plt.axhline(y=0,linestyle='--')
plt.axhline(y=-1.96/np.sqrt(len(air_passengers)),linestyle='--')
plt.axhline(y=1.96/np.sqrt(len(air_passengers)),linestyle='--')
plt.title('Original Autocorrelation plot')
plt.show()     # make no sense

                    # Conclude by the line plot:
                    # - there is an overall trend
                    # - there is seasonality
                    # - therefore before predicting (apply ARIMA), we need to de-trend it



# 2. De-trend by taking log-difference
# taking log because variance is getting bigger and bigger overtime
# take log to try to get to a stationary process
# log transform is 1 to 1 , easy to backtrack
log_air_passengers = np.log(air_passengers.Passengers)
# take difference to take away the seasonality
log_air_passengers_diff = log_air_passengers - log_air_passengers.shift(1)


plt.plot(air_passengers.index, log_air_passengers, color = 'blue')
plt.plot(air_passengers.index, log_air_passengers_diff, color = 'red')
plt.legend(['Log Air_passengers', 'Log-diff Air_passengers'], loc='upper left')
plt.title('De-trend by taking log-difference')
plt.show()
# note difference here， is the 'd' from ARIMA（p, d, q)
# take difference 1 time, d is 1

                    # But note after taking difference:
                    # - we lose the information of the actual values
                    # - therefore we lose info about the mean
                    # - but for ARIMA we are only looking at mean = 0, so shouldn't matter



# 3. Augmented Dickey Fuller test
# - to test whether stationary
# drop nan values from log-diff dataset
log_air_passengers_diff.dropna(inplace=True)

# http://www.statsmodels.org/0.6.1/generated/statsmodels.tsa.stattools.adfuller.html
useful_values_raw = adfuller(log_air_passengers_diff, autolag = 'AIC', regression = 'c')[:5]
useful_values = [v for v in useful_values_raw[:4]]
useful_values.extend([useful_values_raw[4]['1%'], useful_values_raw[4]['5%'], useful_values_raw[4]['10%']])
pd.DataFrame({ 'Value':useful_values, 'Label':['Test Statistic','p-value','#Lags Used','Number of Observations Used', 'Critical value for 1%', 'Critical value for 5%', 'Critical value for 10%']})

                                    # H0: not stationary
                                    # p-value = 0.07 > 0.05
                                    # so can't reject the hypothesis that this is not stationary!
                                    # - so it is not stationary


# 4. Plot ACF, PACF to determine ARIMA(p, d, q)  parameters
#  Let's talk about the ARIMA model
# Auto-Regressive Integrated Moving Average
# In this case we're talking about a series with dependence among values (more natural)
#
#  Nothing but a linear regression with a few times
#  1. The number of Auto-Regressive Terms (p)
#  2. The number of differences taken (d)
#  3. The number of Moving Average Terms (q)

lag_acf = acf(log_air_passengers_diff.values, nlags = 20)
lag_pacf = pacf(log_air_passengers_diff.values, nlags = 20)

# Autocorrelation function plot
plt.bar(x = range(len(lag_acf)), height = lag_acf)
plt.axhline(y=0,linestyle='--')
plt.axhline(y=-1.96/np.sqrt(len(log_air_passengers_diff)), linestyle='--')
plt.axhline(y=1.96/np.sqrt(len(log_air_passengers_diff)), linestyle='--')
plt.title('ACF after de-trend')
plt.show()

                            # ACF for MA(q), approximate as 1
                            # 1. peak at 12, seasonal
                            # 2. ACF cross the upper confidence level at lag = 1.
                            # 3. this ACF plot is for Moving Average MA(q) model , q is approx 1
                            #
                            # - look at where the plot crosses the upper confidence interval for the first time
                            # - for ACF this is 1 and gives us the p value

# pacf plot
plt.bar(x = range(len(lag_pacf)), height = lag_pacf)
plt.axhline(y=0,linestyle='--')
plt.axhline(y=-1.96/np.sqrt(len(log_air_passengers_diff)),linestyle='--')
plt.axhline(y=1.96/np.sqrt(len(log_air_passengers_diff)),linestyle='--')
plt.title('Partial ACF after de-trend')
plt.show()

                            # PACF for AR(p), approximate as 1 or 2
                            # 1. lag = 1 above, but lag = 2 also looks promising
                            # 2. AR(1) or AR(2) model

                            # - look at where the plot crosses the upper confidence interval for the first time
                            # - for PACF this is 2 and gives us the p value


# 5. Apply ARIMA model
# AR model no MA model, cuz generally air passengers would have some correlation with the one before
# p = 2
# d = 1
# q = 0

# note we don't use log_air_passengers_diff, the de-trend one after taking difference
# because we've already specified ARIMA model （2， 1， 0）with 1 for taking difference 1 time
# sub-in log_air_passengers directly

model = ARIMA(log_air_passengers, order=(2, 1, 0))
results_AR = model.fit(disp = -1)

# plot log_air_passengers_diff (actual values)
plt.plot(log_air_passengers_diff, color = 'blue', label = 'Original data after taking difference once')
plt.plot(results_AR.fittedvalues, color='red', label = 'Fitted value by ARIMA(2, 1, 0) model')
# format print the sum squared error
plt.title(f'ARIMA(2,1,0) RSS: {sum((results_AR.fittedvalues-log_air_passengers_diff)**2)}')
plt.show()


# try different values of q
# MA model only, no AR
# AR(0), d = 1, MA(1)
model = ARIMA(log_air_passengers, order = (0, 1, 1))
results_MA = model.fit(disp = -1)

plt.plot(log_air_passengers_diff, color = 'blue', label = 'Original data after taking difference once')
plt.plot(results_MA.fittedvalues, color='red', label = 'Fitted value by ARIMA(0, 1, 1) model')
# title prints out sum squared error
plt.title(f'ARIMA(0,1,1) RSS:{sum((results_MA.fittedvalues-log_air_passengers_diff)**2)}')
plt.show()

# combine above two
# ARIMA model
# try p = 1 or 2
model = ARIMA(log_air_passengers, order=(1, 1, 1))
results_ARIMA = model.fit(disp=-1)

# here use log_air_passengers_diff as original data
plt.plot(log_air_passengers_diff, label = 'Original data after taking difference once')
plt.plot(results_ARIMA.fittedvalues, color='red', label = 'Fitted value by ARIMA(1,1,1) model')
plt.title(f'ARIMA(1,1,1) RSS: {sum((results_ARIMA.fittedvalues-log_air_passengers_diff)**2)}')
# sum squared error 1.45 better than before
plt.show()


# 6. Go back to original data (back out to original form)
# put ARIMA fitted value in a pd.Series
predictions_ARIMA_diff = pd.Series(results_ARIMA.fittedvalues, copy=True)
print(predictions_ARIMA_diff.head())

# get cumulative sum of ARIMA
predictions_ARIMA_diff_cumsum = predictions_ARIMA_diff.cumsum()
print(predictions_ARIMA_diff_cumsum.tail())

# revert the difference = 1 change
predictions_ARIMA_log = pd.Series(log_air_passengers.iloc[0], index=log_air_passengers.index)
predictions_ARIMA_log = predictions_ARIMA_log.add(predictions_ARIMA_diff_cumsum,fill_value=0)
predictions_ARIMA_log.head()

# e as base, take exponential, revert the log transformation
predictions_ARIMA = np.exp(predictions_ARIMA_log)
plt.plot(air_passengers, color = 'blue')
plt.plot(predictions_ARIMA, color = 'red')
plt.title('Original data vs Predicted data using ARIMA(1,1,1)')
plt.show()

# Conclude:
# - untransform it
# - capture the trend
# - doesn't capture seasonality and changing variance (the multiplicative)
# - still useful, can combine with other models to account for the seasonality
#
# - ARIMA didn't factor in changing variance
# - so go for Seasonal ARIMA
# - decompose it to a non-seasonal ARIMA(what we have) + seasonality
# http://www.statsmodels.org/dev/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html
# Confidence interval for ARIMA
# http://statsmodels.sourceforge.net/devel/generated/statsmodels.tsa.arima_model.ARIMAResults.forecast.html#statsmodels.tsa.arima_model.ARMAResults.forecast