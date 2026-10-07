# This is a sample Python script.

# Press Maiusc+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


def deepseek():
    # Hello World created by DeepSeek
    print('Hello, World! (Created by DeepSeek)')


def gemma_helloworld():
    # Hello World created by Gemma
    print('Hello, World! (Created by Gemma)')


def llm_helloworld():
    # Hello World created by an LLM
    print('Hello, World! (Created by an LLM)')


def greet_wife(wife_name):
    # Saluta la moglie con affetto
    print(f"Ciao, {wife_name}! :)")
    print("Spero che la tua giornata sia splendida!")


def greet_wife_custom(wife_name, message=None):
    # Saluta la moglie con un messaggio personalizzato (opzionale)
    if message:
        print(f'Ciao {wife_name}! {message}')
    else:
        print(f'Ciao, {wife_name}! ❤️')


def check_duplicates(input_list):
    # Print the list
    print(f"Lista: {input_list}")
    
    # Check for duplicates
    seen = set()
    has_duplicates = False
    
    for item in input_list:
        if item in seen:
            has_duplicates = True
            print(f"Elemento duplicato trovato: {item}")
        else:
            seen.add(item)
    
    if not has_duplicates:
        print("La lista non contiene duplicati.")
    else:
        print("La lista contiene duplicati.")
    
    return has_duplicates

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
    deepseek()
    gemma_helloworld()
    llm_helloworld()
    print("\nTest check_duplicates:")
    
    # Test with list without duplicates
    list_no_duplicates = [1, 2, 3, 4, 5]
    print(f"\nTest 1: Lista senza duplicati {list_no_duplicates}")
    check_duplicates(list_no_duplicates)
    
    # Saluta la moglie
    print("\nSaluti speciali:")
    print(f"\nTest 3: Saluta la moglie")
    greet_wife('Amorsito')
    greet_wife_custom('Amorsito', 'Buona giornata!')
    list_with_duplicates = [1, 2, 3, 2, 4, 1]
    print(f"\nTest 2: Lista con duplicati {list_with_duplicates}")
    check_duplicates(list_with_duplicates)