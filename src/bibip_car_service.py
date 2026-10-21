from decimal import Decimal
from pathlib import Path
from typing import Final, TypeVar

from pydantic import BaseModel
from sortedcontainers import SortedKeyList

from models import Car, CarFullInfo, CarStatus, Model, ModelSaleStats, Sale

T = TypeVar('T', Car, Model, Sale)


class Response(BaseModel):
    data: str | None = None
    error: str | None = None


class CarService:
    RECORD_WIDTH: Final = 250

    def __init__(self, root_directory_path: str) -> None:
        self.root_directory_path = root_directory_path
        self.__create_data_files()

    @staticmethod
    def __get_entity_index(path_index: Path, index: str) -> Response:
        with open(path_index, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if parts[0] == index:
                    return Response(data=line)

        return Response(error=f'Index {index} not found in {path_index.name}')

    @staticmethod
    def __get_next_line_number(path_index: Path) -> int:
        max_line_number: int = 0

        with open(path_index, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                number: int = int(parts[1])
                if number > max_line_number:
                    max_line_number = number

        return max_line_number + 1

    def __get_entity(self, path: Path, line_number: int) -> Response:
        with open(path, 'r', encoding='utf-8') as f:
            offset = (line_number - 1) * (self.RECORD_WIDTH + 1)
            f.seek(offset)
            line = f.readline()
            if not line:
                return Response(error=f'Line_number {line_number} not found in {path.name}')
            line = line.strip()
            return Response(data=line)

    @staticmethod
    def __get_all_data(path: Path) -> list[str]:
        data = []

        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data.append(line)

        return data

    @staticmethod
    def __get_fixed_string(text: str, width: int, fillchar: str = ' ') -> Response:
        if not text.isascii():
            return Response(error=f'Record contains non-ASCII characters: {text!r}')
        if len(text) > width:
            return Response(error=f'Record too long: {len(text)} chars, allowed {width}')
        return Response(data=text.ljust(width, fillchar))

    def __create_data_files(self):
        Path(self.root_directory_path, 'data').mkdir(parents=True, exist_ok=True)
        self.models_path_index = Path(self.root_directory_path, 'data/models_index.txt')
        self.models_path = Path(self.root_directory_path, 'data/models.txt')
        self.cars_path_index = Path(self.root_directory_path, 'data/cars_index.txt')
        self.cars_path = Path(self.root_directory_path, 'data/cars.txt')
        self.sales_path_index = Path(self.root_directory_path, 'data/sales_index.txt')
        self.sales_path = Path(self.root_directory_path, 'data/sales.txt')
        for p in (self.models_path_index,
                  self.models_path,
                  self.cars_path_index,
                  self.cars_path,
                  self.sales_path_index,
                  self.sales_path):
            p.touch(exist_ok=True)

    def __add_entity(self, entity: T, path: Path) -> Response:
        json = entity.model_dump_json()
        response = self.__get_fixed_string(json, width=self.RECORD_WIDTH)

        if response.data is None:
            return Response(error=response.error)

        with open(path, 'a', encoding='utf-8') as f:
            f.write(f'{response.data}\n')

        return Response(data=json)

    def __add_entity_index(self, path_index: Path, entity_index: str) -> str:
        data = self.__get_all_data(path_index)
        data.append(entity_index)

        sorted_list = SortedKeyList(data, key=lambda x: x.split(',')[0])

        with open(path_index, 'w', encoding='utf-8') as f:
            for line in sorted_list:
                f.write(f'{line}\n')

        return entity_index

    def __update_entity_index(self, path_index: Path, index: str, new_index: str) -> Response:
        entity_index = self.__get_entity_index(path_index, index)
        if entity_index.data is None:
            return Response(error=entity_index.error)

        new_entity_index = self.__get_entity_index(path_index, new_index)
        if new_entity_index.data:
            return Response(error=f'New index {new_index} already exists')

        data: list[str] = [f'{new_index},{e.split(",")[1]}' if e.split(',')[0] == index
                           else e for e in self.__get_all_data(path_index)]

        sorted_list = SortedKeyList(data, key=lambda x: x.split(',')[0])

        with open(path_index, 'w', encoding='utf-8') as f:
            for line in sorted_list:
                f.write(f'{line}\n')

        return Response(data=f'{new_index},{entity_index.data.split(",")[1]}')

    def __update_entity(self, entity: T, path: Path, line_number: int) -> Response:
        with open(path, 'r+', encoding='utf-8') as f:
            offset = (line_number - 1) * (self.RECORD_WIDTH + 1)
            f.seek(offset)
            response = self.__get_fixed_string(entity.model_dump_json(), width=self.RECORD_WIDTH)
            if response.data is None:
                return Response(error=response.error)
            f.write(f'{response.data}\n')

        return Response(data=entity.model_dump_json())

    # Задание 1. Сохранение автомобилей и моделей
    def add_model(self, model: Model) -> Model | None:
        index = self.__get_entity_index(self.models_path_index, str(model.index()))
        if index.data:
            print(f'Model with index {index.data.split(",")[0]} already exists')
            return None

        next_line_number = self.__get_next_line_number(self.models_path_index)
        self.__add_entity_index(self.models_path_index, f'{str(model.index())},{next_line_number}')

        entity = self.__add_entity(model, path=self.models_path)
        if entity.data is None:
            print(entity.error)
            return None

        return model

    # Задание 1. Сохранение автомобилей и моделей
    def add_car(self, car: Car) -> Car | None:
        model_index = self.__get_entity_index(self.models_path_index, str(car.model))
        if model_index.data is None:
            print(f'{model_index.error}, model is required before adding car')
            return None

        car_index = self.__get_entity_index(self.cars_path_index, str(car.index()))
        if car_index.data:
            print(f'Car with index {car_index.data.split(",")[0]} already exists')
            return None

        next_line_number = self.__get_next_line_number(self.cars_path_index)
        self.__add_entity_index(self.cars_path_index, f'{str(car.index())},{next_line_number}')

        entity = self.__add_entity(car, path=self.cars_path)
        if entity.data is None:
            print(entity.error)
            return None

        return car

    # Задание 2. Сохранение продаж.
    def sell_car(self, sale: Sale) -> Sale | None:
        car_index = self.__get_entity_index(self.cars_path_index, sale.index())
        if car_index.data is None:
            print(f'{car_index.error}, car is required before selling car')
            return None

        sale_index = self.__get_entity_index(self.sales_path_index, sale.index())
        if sale_index.data:
            print(f'Sale with index {sale_index.data.split(",")[0]} already exists')
            return None

        next_line_number = self.__get_next_line_number(self.sales_path_index)
        self.__add_entity_index(self.sales_path_index, f'{sale.index()},{next_line_number}')

        sale_entity = self.__add_entity(sale, path=self.sales_path)
        if sale_entity.data is None:
            print(sale_entity.error)
            return None

        car_line_number = int(car_index.data.split(',')[1])
        car_entity = self.__get_entity(self.cars_path, car_line_number)
        if car_entity.data is None:
            print(car_entity.error)
            return None

        car = Car.model_validate_json(car_entity.data)
        car.status = CarStatus.sold
        update_entity = self.__update_entity(car, path=self.cars_path, line_number=car_line_number)
        if update_entity.data is None:
            print(update_entity.error)
            return None

        return sale

    # Задание 3. Доступные к продаже
    def get_cars(self, status: CarStatus) -> list[Car]:
        cars: list[Car] = []

        with open(self.cars_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                car = Car.model_validate_json(line)
                if car.status == status:
                    cars.append(car)

        return cars

    # Задание 4. Детальная информация
    def get_car_info(self, vin: str) -> CarFullInfo | None:
        car_index = self.__get_entity_index(self.cars_path_index, vin)
        if car_index.data is None:
            print(car_index.error)
            return None

        car_line_number = int(car_index.data.split(',')[1])
        car_response = self.__get_entity(self.cars_path, car_line_number)
        if car_response.data is None:
            print(car_response.error)
            return None

        car = Car.model_validate_json(car_response.data)

        model_index = self.__get_entity_index(self.models_path_index, str(car.model))
        if model_index.data is None:
            print(model_index.error)
            return None

        model_line_number = int(model_index.data.split(',')[1])
        model_response = self.__get_entity(self.models_path, model_line_number)
        if model_response.data is None:
            print(model_response.error)
            return None

        model = Model.model_validate_json(model_response.data)

        sale_index = self.__get_entity_index(self.sales_path_index, vin).data
        sale_line_number = int(sale_index.split(',')[1]) if sale_index else None
        sale_response = self.__get_entity(self.sales_path, sale_line_number) if sale_line_number else None

        sale = Sale.model_validate_json(sale_response.data) if sale_response and sale_response.data else None
        return CarFullInfo(vin=vin,
                           car_model_name=model.name,
                           car_model_brand=model.brand,
                           price=car.price,
                           date_start=car.date_start,
                           status=car.status,
                           sales_date=sale.sales_date if sale else None,
                           sales_cost=sale.cost if sale else None)

    # Задание 5. Обновление ключевого поля
    def update_vin(self, vin: str, new_vin: str) -> Car | None:
        update_car_index = self.__update_entity_index(self.cars_path_index, vin, new_vin)
        if update_car_index.data is None:
            print(f'{update_car_index.error}, vin can not be updated')
            return None

        car_line_number = int(update_car_index.data.split(',')[1])
        get_entity = self.__get_entity(self.cars_path, car_line_number)
        if get_entity.data is None:
            print(get_entity.error)
            return None

        car = Car.model_validate_json(get_entity.data)
        car.vin = new_vin
        update_car = self.__update_entity(car, self.cars_path, car_line_number)
        if update_car.data is None:
            print(update_car.error)
            return None

        sale_index = self.__get_entity_index(self.sales_path_index, vin)
        if sale_index.data is None:
            return car

        update_sale_index = self.__update_entity_index(self.sales_path_index, vin, new_vin)
        if update_sale_index.data is None:
            print(update_sale_index.error)
            return None

        sale_line_number = int(sale_index.data.split(',')[1])
        sale_entity = self.__get_entity(self.sales_path, sale_line_number)
        if sale_entity.data is None:
            print(sale_entity.error)
            return None

        sale = Sale.model_validate_json(sale_entity.data)
        sale.car_vin = new_vin
        update_sale_entity = self.__update_entity(sale, self.sales_path, sale_line_number)
        if update_sale_entity.data is None:
            print(update_sale_entity.error)
            return None

        return car

    # Задание 6. Удаление продажи
    def revert_sale(self, sales_number: str) -> Car | None:
        sale_line_number: int | None = None
        with open(self.sales_path, 'r', encoding='utf-8') as f:
            for num, line in enumerate(f, 1):
                line = line.strip()
                sale = Sale.model_validate_json(line)
                if sale.sales_number == sales_number:
                    sale_line_number = num
                    break

        if sale_line_number is None:
            print(f'Sale with sales_number {sales_number} not found in {self.sales_path.name}')
            return None

        sale_entity = self.__get_entity(self.sales_path, sale_line_number)
        if sale_entity.data is None:
            print(sale_entity.error)
            return None

        sale = Sale.model_validate_json(sale_entity.data)
        sale.is_deleted = True

        update_sale_entity = self.__update_entity(sale, self.sales_path, sale_line_number)
        if update_sale_entity.data is None:
            print(update_sale_entity.error)
            return None

        car_index = self.__get_entity_index(self.cars_path_index, sale.car_vin)
        if car_index.data is None:
            print(car_index.error)
            return None

        car_line_number = int(car_index.data.split(',')[1])
        car_entity = self.__get_entity(self.cars_path, car_line_number)
        if car_entity.data is None:
            print(car_entity.error)
            return None

        car = Car.model_validate_json(car_entity.data)
        car.status = CarStatus.available
        update_car = self.__update_entity(car, self.cars_path, car_line_number)
        if update_car.data is None:
            print(update_car.error)
            return None

        return car

    # Задание 7. Самые продаваемые модели
    def top_models_by_sales(self) -> list[ModelSaleStats]:
        data = self.__get_all_data(self.sales_path)
        obj: dict[str, list[int | Decimal]] = {}

        for elem in data:
            sale = Sale.model_validate_json(elem)
            if sale.is_deleted:
                continue
            vin = sale.car_vin
            car_index = self.__get_entity_index(self.cars_path_index, vin)
            if car_index.data is None:
                continue
            car_line_number = int(car_index.data.split(',')[1])
            car_entity = self.__get_entity(self.cars_path, car_line_number)
            if car_entity.data is None:
                continue
            car = Car.model_validate_json(car_entity.data)
            model_index = self.__get_entity_index(self.models_path_index, str(car.model))
            if model_index.data is None:
                continue
            model_entity = self.__get_entity(self.models_path, int(model_index.data.split(',')[1]))
            if model_entity.data is None:
                continue

            if model_entity.data in obj:
                obj[model_entity.data] = [obj[model_entity.data][0] + 1, obj[model_entity.data][1] + sale.cost]
            else:
                obj[model_entity.data] = [1, sale.cost]

        sorted_list = SortedKeyList(obj.items(), key=lambda item: (-item[1][0], -item[1][1]))
        top_3 = sorted_list[:3]

        result = []
        for elem in top_3:
            model = Model.model_validate_json(elem[0])
            sales_number = elem[1][0]
            model_sale_stats = ModelSaleStats(car_model_name=model.name, brand=model.brand, sales_number=sales_number)
            result.append(model_sale_stats)

        return result
