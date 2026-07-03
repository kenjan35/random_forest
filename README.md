# Random forest

## Objective
We want detect fuel theft of a generator.

First of all, we need understand our data, it's **data exploration**.

After that, we need understand what is temporal window. (Just a set of data which can be used for Machine Learning)

So we need to transform our CSV file into temporal window, in that way we can proceed to Random Forest algorithm.

1. Transformation of data
We need to transform all our CSV into window :
```sh
Window 1

180
179.9
179.8
179.8
179.7
```
Then :
```sh
Window 2

179.9
179.8
179.8
179.7
179.6
```
And then :
```sh
Window 3

179.8
179.8
179.7
179.6
179.5
```

The model will learn to recognize the window's form.

There's 2 essentials parameters :
- window_size : How many lines does the window contain.
- stride : By how many steps does the window shift.

## Useful function
### Numpy

- array : this function is used to create a numpy array.
- shape : A tuple showing the length of each dimension of an ndarray.

```sh
import numpy as np

data = np.array([180, 176.2, 176.3])

# It will print <class 'numpy.ndarray'>. ndarray means N-Dimensional Array.
print(type(data))

# It will print (3,). It means 3 values.
print(data.shape)

fuel = np.array([
    [180,179,178],
    [177,176,175]
])

# It will print (2,3). It means 2 lines and 3 columns.
print(fuel.shape)

windows = np.array([
    [180,179,178,177,176],
    [179,178,177,176,175],
    [178,177,176,175,174]
])

# It will print (3,5). It means 3 windows and 5 measurements per window.
print(windows.shape)
```

### Pandas

- read_csv : read a CSV file
- head : return all first lines
- columns : return all column's real name

```sh
import pandas as pd

df = pd.read_csv("Normal_1.csv")

# It will print pandas.core.frame.DataFrame. A DataFrame is like an Excel sheet in memory.
print(type(df))

# It will print first lines to check if file loads successfully.
print(df.head())

print(df.columns)

# fuel become a Series pandas. A Series is a column.
fuel = df["Fuel Volume"]
```

## Role of each library

- pandas : read and manipulate all data tables (CSV, Excel, ...)
- numpy : perform quick calculations on numerical data
- scikit-learn : train the Machine Learning model

