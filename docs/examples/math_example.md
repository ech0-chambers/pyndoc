# Sample Assignment

<!-- We'll use numpy to generate random parameters for the questions -->

%{
    from numpy.random import randint
}


## Question 1
%{
    m = tex.var("m", randint(5, 10))            # kg
    C = tex.var("C", 8.056)                     # J/(kg K)
    dT = tex.var("\Delta T", randint(10, 30))   # K
    E = tex.var("E", m * C * dT)                # J
}

You are given a sample of metal and asked to determine its specific heat. You weigh the sample and find that it has a mass of %%md.math(m(unit = r'\kilo\gram')). You carefully add %%md.math(E('.4e', r'\joule')) of heat energy to the sample and find that its temperature rises by %%md.math(dT(unit = r'\celsius')). What is the specific heat of the metal?

### Solution
The specific heat capacity is the energy required to raise the temperature of a unit mass of a substance by one degree:
%%md.equation(
    tex.split([
        C * tex.alignment == E / (m * dT),
        tex.alignment == E('.3el') / (m() @ dT()),
        tex.alignment == (E / (m * dT))('.3f')
    ])
)

So, the specific heat capacity is %%md.math(C == C('.3f', unit = r"\joule\per\kilo\gram\per\kelvin")).

## Question 2

%{
    m = tex.var("m", randint(2, 6) * 0.05)  # kg
    P = tex.var("P", randint(3, 6) * 50)    # W
    T0 = tex.var("T_0", randint(20, 30))    # C
    T1 = tex.var("T_1", randint(40, 50))    # C
    dT = tex.var("\Delta T", T1 - T0)       # C
    C = tex.var("C", 4180)                  # J/(kg K) (water)
    E = tex.var("E", m * C * dT)            # J
}

In an effort to stay awake for an all-night study session, a student makes a cup of coffee by first heating %%md.math(m(unit = r'\kilo\gram')) in a %%md.math(P(unit = r'\watt')) kettle. How much heat must be added to the water to raise its temperature from %%md.math(T0(unit = r'\celsius')) to %%md.math(T1(unit = r'\celsius'))?

### Solution

The specific heat capacity of water is %%md.math(C == C('.0f', unit = r"\joule\per\kilo\gram\per\kelvin")). The energy required to raise the temperature of a substance is given by:
%%md.equation(
    tex.split([
        E * tex.alignment == m * C * dT,
        tex.alignment == m() @ C() @ dT(),
        tex.alignment == (m * C * dT)('.2el')
    ])
)

So, the total amount of energy needed is %%md.math(E('.2e', unit = r"\joule")), or %%md.math((E / 1e3)('.1f', unit = r'\kilo\joule')).

## Question 3

%{
    t = tex.var("t", E / P)                             # s
    t_min = tex.var("t_{min}", int(float(t) // 60)) # min
    t_sec = tex.var("t_{sec}", int(round(float(t)) % 60))  # s
}

In the previous problem, how much time is required to heat the water? Assume that all of
the kettle’s power goes into heating the water

### Solution

The power is given as %%md.math(P(unit = r'\watt')). The time required to heat the water is given by:
%%md.equation(
    tex.split([
        t * tex.alignment == E / P,
        tex.alignment == E() / P(),
        tex.alignment == (E / P)('.0f', r'\second')
    ])
)

Or, %%md.math(t_min(unit = r'\minute')) and %%md.math(t_sec(unit = r'\second')).