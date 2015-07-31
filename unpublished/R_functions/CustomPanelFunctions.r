library(lattice)

# simulate correlated data
n <- 200
x <- rnorm(n, mean=0, sd=1)
y <- x * rnorm(n, mean=2, sd=2) + rnorm(n, mean=5, sd=1)

# simulate two levels of grouping
g <- gl(n=4, k=25, length=n, labels=letters[1:4])
f <- gl(n=2, k=50, length=n, labels=c('g1', 'g2'))

# combine into DF
d <- data.frame(x, y, g, f)

# define a custom panel function
# note that "..." passes all of the default arguments from parent function
# to child function(s)
newPanelFunction <- function(...) {
   # normally called by xyplot() to do routine plotting
   panel.superpose(...)
   # add regression line ignoring groups
   panel.lmline(..., col='black', lwd=2, lty=2)
}

# plot y ~ x, with points, grid, and group-wise regression line
# use custom panel function, to add regression line for entire data set
xyplot(y ~ x, groups=g, data=d, type=c('p','g', 'r'), 
auto.key=list(columns=4, points=TRUE, lines=FALSE),
panel=newPanelFunction)

# works seamlessly with multiple panels
xyplot(y ~ x | f, groups=g, data=d, type=c('p','g', 'r'), 
auto.key=list(columns=4, points=TRUE, lines=FALSE),
panel=newPanelFunction)
