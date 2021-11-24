import requests
import json
from datetime import datetime

from requests import status_codes
def space_print():
    print("")
    print("--//--"*15)
    print("")

def main(url):
    
    
    #s = requests.Session()
    s = requests.Session()
    r = s.get(f'{url}/tasks/get_tasks')
    if r.status_code !=200:
        print(f"Error to connect to server. Status code {status_codes}")
        return
    csrf_token = s.cookies['csrftoken']

    # csrf_token = r.json()['csrf_token']


    while True:
        digito = int(input("Digite:\n1: Get\n2: Post\n3: Delete\n0: Sair"))
        if digito ==1:
            r = requests.get(f'{url}/tasks/get_tasks')
            if r.status_code==200:
                print("RESULTADO:")
                print(json.dumps(r.json(), indent=4, sort_keys=True))
                space_print()
            else:
                print(f"Não foi possivel estabelecer conexão com o servidor. Status Code:{r.status_code}")
        elif digito ==2:
            now = datetime.now()
            current_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"Utilizando hora atual: {current_time}")
            title = input("Title:")
            description = input("Description")
            
            login_data = dict(title=title, pub_date=current_time,description=description)

            r = s.post(f'{url}/tasks/post_task', data={'csrfmiddlewaretoken': csrf_token,'title': title, 'pub_date': current_time, 'description': description})
            print(r.status_code)
            print(r.text)
        elif digito ==3:
            id_=int(input("Qual id deseja deletar?"))
            r = requests.get(f'{url}/tasks/delete_task/{id_}')
            print(r.status_code)
            if r.status_code == 200:
                print("ID deletado")
            else:
                print(f"Erro ao deletar ID {id_}")
        elif digito == 0:
            break


if __name__ == "__main__":

    main("http://localhost:8080")
