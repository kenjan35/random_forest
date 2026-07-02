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
