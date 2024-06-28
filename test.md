
%{
    a = tex.var("a", 3)
    b = tex.var("b", 4)
    c = tex.var("c", (a **2 + b ** 2)**0.5)
}

Pythagoras' theorem states that for a triangle with side lengths %%md.math(a), %%md.math(b), and %%md.math(c), the following relationship holds:
%%md.equation(
    a ** 2 + b ** 2 == c ** 2
)

For example, if %%md.math(a == a()) and %%md.math(b == b()), then 
%%md.equation(
    (c == tex.sqrt(a() ** 2 + b() ** 2)) == c()
)