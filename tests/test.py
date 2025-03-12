from drl_forex_trading_internal.data.resampler import DataResampler

pair_name='EURUSD'
timeframe= '1h'
start_date="2025-03-01"
end_date="2025-03-11"
    # Get resampled data for training
resampler = DataResampler()
training_data = resampler.get_resampled_price_data(
    pair_name, timeframe, start_date, end_date
)
    
print(training_data)
    