#!/usr/bin/python
# coding: utf-8
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## HVAC Formulas

from math import exp, log

def p_ws(F):
    '''
    Computation of the saturation pressure from temperature.
    
    @var F: float temperature in F

    The saturation pressure over liquid water for the temperature range
    of 32 to 392°F is given by

    2009 ASHRAE Handbook ­– Fundamentals Chapter 1 equation 6
    '''
    T=F+459.67

    C8=  -1.0440397E+04
    C9=  -1.1294650E+01
    C10= -2.7022355E-02
    C11= +1.2890360E-05
    C12= -2.4780681E-09
    C13= +6.5459673E+00

    return exp(C8/T + C9 + C10*T + C11*T**2 + C12*T**3 + C13*log(T))

def h(F,rh,p=14.7):
    '''
    Computation of enthalpy (and W)
    
    @var F: float temperature in F
    @var rh: float relative hummidty in an integer 1-100
    @var p: float pressure in psia  

    2009 ASHRAE Handbook – Fundamentals Chapter 1
    '''
    pw=(rh/100.0)*p_ws(F) ## Eq 24
    W=0.621945*pw/(p-pw) ## Eq 22
    return 0.240*F + W*(1061+0.444*F) ## Eq 32
