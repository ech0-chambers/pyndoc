<!-- To be compiled including `packages.tex` in the header -->

# Sample Assignment

<!-- We'll use numpy to generate random parameters for the questions -->

%{
    from numpy.random import randint
}


## Question 1
%{
    m = tex.var("m", randint(5, 10), unit = 'kg')
    C = tex.var("C", 8.056, unit = 'J/kg/K')
    dT = tex.var("\Delta T", randint(10, 30), unit = 'K')
    E = tex.var("E", m * C * dT, fmt = '.4e') # unit (joule) is inferred from the expression
}

You are given a sample of metal and asked to determine its specific heat. You weigh the sample and find that it has a mass of %%m(). You carefully add %%E() of heat energy to the sample and find that its temperature rises by %%dT(). What is the specific heat of the metal?

### Solution
The specific heat capacity is the energy required to raise the temperature of a unit mass of a substance by one degree:
%%md.equation(
    tex.split([
        [C, E / (m * dT)],
        [E() / (m() @ dT())],
        [(E / (m * dT))('.3f')]
    ])
)

So, the specific heat capacity is %%(C == C()).

## Question 2

%{
    del m # remove the previous variable for redefinition
    tex.symbols(f"""
        m = {randint(2, 6) * 0.05} kg;
        P = {randint(3, 10) * 50} W;
        T_0 = {randint(20, 30)} celsius;
        T_1 = {randint(80, 100)} celsius;    
    """, globals())
    dT = tex.var("\Delta T", T_1 - T_0)
    C = tex.var("C", 4180, unit = 'J/kg/K')
    E = tex.var("E", m * C * dT)
}

In an effort to stay awake for an all-night study session, a student makes a cup of coffee by first heating %%m() of water in a %%P() kettle. How much heat must be added to the water to raise its temperature from %%T_0() to %%T_1()?

### Solution

The specific heat capacity of water is %%(C == C()). The energy required to raise the temperature of a substance is given by:
%%md.equation(
    tex.split([
        [E, m * C * dT],
        [m() @ C() @ dT()],
        [(m * C * dT)()]
    ])
)

So, the total amount of energy needed is %%E(), or %%E(unit = r'kJ').

## Question 3

%{
    t = tex.var("t", E / P, fmt = '.0f') # seconds, inferred from the expression
    t_min, t_sec = divmod(float(t), 60)
    t_min = tex.var("t_{min}", t_min, unit = 'minute')
    t_sec = tex.var("t_{sec}", t_sec, unit = 'second', fmt = '.0f')
}

In the previous problem, how much time is required to heat the water? Assume that all of
the kettle’s power goes into heating the water

### Solution

The power is given as %%P(). The time required to heat the water is given by:
%%md.equation(
    tex.split([
        [t, E / P],
        [E() / P()],
        [(E / P)()]
    ])
)

Or, %%t_min() and %%t_sec().