def division(a,b):
    if b == 0:
        return 0
    return a/b
    def hello_world(request):
        return JsonResponse({'Hello': 'World'})


def test_division():
    assert division(10,0) == 0