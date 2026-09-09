function login(username,password){
    return username === "admin" && password === "1234";
}

test("valid login" , () => {
    expect(login("admin","1234")).toBe(true);
});

test("invalid login" , () =>{
    expect(login("admin","wrong")).toBe(false)
});