from django.shortcuts import render

from initiatives.models import Category


CATEGORY_EXAMPLES = {
    "Благоустройство": [
        "ремонт детской площадки во дворе",
        "установка скамеек и освещения в сквере",
        "обустройство удобной зоны отдыха для жителей",
    ],
    "Культура": [
        "создание уличной книжной зоны",
        "проведение районного фестиваля или выставки",
        "оборудование пространства для творчества жителей",
    ],
    "Образование": [
        "бесплатные занятия по цифровой грамотности",
        "развитие учебного пространства в библиотеке",
        "городские лекции и профориентационные мероприятия",
    ],
    "Спорт": [
        "ремонт дворовой спортивной площадки",
        "установка уличных тренажёров",
        "организация бесплатных спортивных занятий",
    ],
    "Транспорт": [
        "обустройство безопасного пешеходного перехода",
        "установка велопарковок",
        "улучшение остановки общественного транспорта",
    ],
    "Экология": [
        "установка контейнеров для раздельного сбора отходов",
        "озеленение двора или общественной территории",
        "уборка берега и экологические мероприятия для жителей",
    ],
}


def home(request):
    return render(request, "home.html")

def about(request):
    return render(
        request,
        "about.html"
    )

def how_to_use(request):
    category_guides = [
        {
            "category": category,
            "examples": CATEGORY_EXAMPLES.get(category.name, []),
        }
        for category in Category.objects.all()
    ]
    return render(
        request,
        "how_to_use.html",
        {"category_guides": category_guides},
    )

def contacts(request):
    return render(
        request,
        "contacts.html"
    )


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
