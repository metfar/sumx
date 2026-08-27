# sumX modern runtime values
SET CAPS_SENSITIVE OFF;
Name = "Ana";
? name;                 # same variable

A = [10, 20, 30, 40];
A[1] = 99;
? A[1:3];

D = {"Name":"Ana", "name":"Maria"};
? D["Name"];
? D["name"];

person = OBJ(
 name="Ana",
 active=ON,
 phones=["099111111", "29001111"]
);
person.phones.append("555-0100");
? person.name;
? person.phones[-1];

memo = """This is a multiline value;
# this hash is data because it is inside the string.
""";
? memo;
