# Nuclear Fusion in Stars

%%%py{atomic.py}

Within stars, the most common fusion reaction is the proton-proton chain, which is a series of reactions that convert hydrogen into helium. The overall reaction is:

%%nuclear_reaction{{6 H -> He + 2 H + 2 e^{+} + 2 \nu_e}}

Once enough helium has been produced, the helium nuclei themselves will have an appreciable chance of fusing. Two helium nuclei can undergo the interaction

%%nuclear_reaction{{He + He -> Be\,.}}

However, this is extremely unstable and will quickly undergo the reverse reaction with a lifetime of around $10^{-16}\,\text{s}$. If, however, the %%isotope("Be", 8) nucleus collides with another helium nucleus before it decays, it can undergo the reaction

%%nuclear_reaction{{8Be + He -> C\,.}}

When enough carbon has been formed, a new cycle can begin in which %%element{{C}} becomes a catalyst for the formation of %%element{{He}} in the following chain:

%{
    cycle = [
        "C + H & -> 13N + \\gamma",
        "13N & -> 13C + e^+ + \\nu_e",
        "13C + H & -> N + \\gamma",
        "N + H & -> 15O + \\gamma",
        "15O & -> 15N + e^+ + \\nu_e",
        "15N + H & -> C + He"
    ]
}

%%md.equation(
    tex.split([
        nuclear_reaction_string(r) for r in cycle
    ])
)

The carbon acts as a catalyst; the %%element{{C}} atom is consumed in the first reaction and regenerated in the last. The total energy released in this cycle is the same as in the proton-proton chain, but in the carbon cycle slightly more of that energy is lost via the neutrinos. However, the rate of the carbon cycle is much higher than the proton-proton chain.

Once the core of the star heats sufficiently, further reactions can occur to create heavier elements:

%{
    reactions = [
        "C  + He & -> O",
        "O  + He & -> Ne",
        "Ne + He & -> Mg",
    ]
}

%%md.equation(
    tex.split([
        nuclear_reaction_string(r) for r in reactions
    ])
)

If these atoms are ejected into the cooler regions of the star, where the proton-proton cycle is still dominant, then they can capture protons to form elements with odd $Z$:

%{
    reactions = [
        "O  + H & -> F",
        "Ne + H & -> Na",
        "Mg + H & -> Al",
    ]
}

%%md.equation(
    tex.split([
        nuclear_reaction_string(r) for r in reactions
    ])
)

As the core of the star heats further, these heavier nuclei can combine to form even larger elements, up to and including %%element{{Fe}}. However, we find that elements heavier than iron are not formed in stars via fusion.