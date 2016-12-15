import json

def files(file, operation, data = None):
    if operation == "save" and data != None:
        with open(file, encoding = 'utf-8', mode = 'w') as f:
            f.write(json.dumps(data, indent = 4, sort_keys = True, separators = (',',' : ')))
    elif operation == "load" and data == None:
        with open(file, encoding = 'utf-8', mode = "r") as f:
            return json.loads(f.read())
    elif operation == "check" and data == None:
        try:
            with open(file, encoding = 'utf-8', mode = "r") as f:
                return True
        except:
            return False
    else:
        raise("Invalid")

