import aiohttp
from random import choices

from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from googletrans import Translator
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router, types

router = Router()
translator = Translator()


class OrderRecipes(StatesGroup):
    waiting_for_category = State()
    waiting_for_recipe = State()

@router.message(Command("category_search_random"))
async def show_categories(message: Message, command: CommandObject, state: FSMContext):
    if command.args is None:
        await message.answer(
            "Ошибка: не передано количество рецептов"
        )
        return
    try:
        await state.set_data({"number_of_recipes": int(command.args)})
    except ValueError:
        await message.answer('Пожалуйста, укажите правильное количество рецептов')
        return
    async with aiohttp.ClientSession() as session:
        url = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
        async with session.get(url) as response:
            data = await response.json()
            categories = data['meals']
            builder = ReplyKeyboardBuilder()
            for category in categories:
                builder.add(types.KeyboardButton(text=category['strCategory']))
            builder.adjust(4)

        await message.answer('Выберите категорию:',
                             reply_markup=builder.as_markup(resize_keyboard=True)
                             )
        await state.set_state(OrderRecipes.waiting_for_category.state)


@router.message(OrderRecipes.waiting_for_category)
async def show_recipes(message: types.Message, state: FSMContext):
    data = await state.get_data()

    async with aiohttp.ClientSession() as session:
        url = f'https://www.themealdb.com/api/json/v1/1/filter.php?c={message.text}'
        async with session.get(url) as response:
            meals = await response.json()
            chosen_meals = choices(meals['meals'], k=data["number_of_recipes"])
            meals_id = [meal['idMeal'] for meal in chosen_meals]
        await state.set_data({"meals_id": meals_id})
        kb = [[
            types.KeyboardButton(text="Покажи рецепты"),
        ],
        ]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True,
        )
        await message.answer(
            f'Как Вам такие варианты: '
            f'{", ".join([translator.translate(meal["strMeal"], dest="ru").text for meal in chosen_meals])}',
            reply_markup=keyboard
        )
        await state.set_state(OrderRecipes.waiting_for_recipe.state)


@router.message(OrderRecipes.waiting_for_recipe)
async def show_full_recipe(message: types.Message, state: FSMContext):
    data = await state.get_data()

    async with aiohttp.ClientSession() as session:
        for meal in data['meals_id']:
            url = f'https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal}'
            async with session.get(url) as response:
                meal_info = await response.json()
                meal_name = translator.translate(meal_info['meals'][0]['strMeal'],dest='ru').text
                meal_instruction = translator.translate(meal_info['meals'][0]['strInstructions'],dest='ru').text
                meal_ingredients = []
                for index in range(1,21):
                    if meal_info['meals'][0][f'strIngredient{index}']:
                        meal_ingredients.append(translator.translate(meal_info['meals'][0][f'strIngredient{index}'], dest='ru').text)
                    else:
                        break
            await message.answer(
                f'{meal_name}\n\n'
                f'Ингредиенты: {", ".join(meal_ingredients)}\n\n'
                f'Рецепт:\n {meal_instruction}',

            )