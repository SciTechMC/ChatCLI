def prod():
    data = {
        "user" : "production_chatcli",
        "password" : "S3cret#Code1234",
        "db" : "chatcli_prod"
    }
    return data

def dev():
    data = {
        "user" : "chatcli_access",
        "password" : "test1234",
        "db" : "chatcli_dev"
    }
    return data