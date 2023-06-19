from aiohttp import web
from models import engine, Base, User, AdsTable, Session
import json
from sqlalchemy.future import select
from bcrypt import hashpw, gensalt, checkpw
from sqlalchemy.exc import IntegrityError


app = web.Application()

async def app_context(app):
    async with engine.begin() as con:
        await con.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()



async def get_user(user_id, session):
    user = await session.get(User, user_id)
    if user is None:
        raise web.HTTPNotFound(
            text=json.dumps({
                'status': 'error',
                'message': 'user not found'
            }),
            content_type='application/json'
        )
    return user

async def get_ads(ads_id, session):
    ads = await session.get(AdsTable, ads_id)
    if ads is None:
        raise web.HTTPNotFound(
            text=json.dumps({
                'status': 'error',
                'message': 'advertisement not found'
            }),
            content_type='application/json'
        )
    return ads

async def get_user_name(user_name, session):
    """
    Получение пользователя по email
    :param user_name: email
    """
    user = await session.execute(select(User).filter(User.email == user_name))
    if not user:
        raise web.HTTPNotFound(
            text=json.dumps({
                'status': 'error',
                'message': 'user not found'
            }),
            content_type='application/json'
        )
    return user.scalars().all()


async def get_permission(json_data):
    """
    Функция проверяет соответствие поступаемых данных пользователя (email и password) с данными в базе
    :param json_data:
    :return: json_data
    """
    async with Session() as session:
        user = await get_user_name(json_data.pop('username'), session)
        password = json_data.pop('password')
        password = password.encode()
        if user:
            check = checkpw(password, user[0].password.encode())
            if check:
                json_data['username'] = user[0].id
                return json_data
        raise web.HTTPUnauthorized(
            text=json.dumps({
                'status': 'error',
                'message': 'user not found'
            }),
            content_type='application/json'
        )


def hash_password(password: str):
    """
    Хэширование пароля с помощью bcrypt
    :return:
    """
    password = password.encode()
    password = hashpw(password, salt=gensalt())
    password = password.decode()
    return password

@web.middleware
async def session_middleware(request: web.Request, handler):
    async with Session() as session:
        request['session'] = session
        response = await handler(request)
        return response

class AdsView(web.View):

    async def post(self):
        json_data = await self.request.json()
        json_data = await get_permission(json_data)
        new_ads = AdsTable(**json_data)
        self.request['session'].add(new_ads)
        await self.request['session'].commit()
        return web.json_response({
            'id': new_ads.id,
            'head': new_ads.head,
            'description': new_ads.description,
            'user': new_ads.username
        })

    async def get(self):
        ads = await get_ads(int(self.request.match_info['ads_id']), self.request['session'])
        return web.json_response({
            'id': ads.id,
            'head': ads.head,
            'description': ads.description
        })

    async def patch(self):
        json_data = await self.request.json()
        json_data = await get_permission(json_data)
        ads = await get_ads(int(self.request.match_info['ads_id']), self.request['session'])
        if not (json_data['username'] == ads.username):
            raise web.HTTPUnauthorized(
                text=json.dumps({
                    'status': 'error',
                    'message': 'wrong user'
                }),
                content_type='application/json'
            )
        for field, value in json_data.items():
            setattr(ads, field, value)
        await self.request['session'].commit()
        return web.json_response({
            'id': ads.id,
            'head': ads.head,
            'description': ads.description,
            'user': ads.username
        })

    async def delete(self):
        json_data = await self.request.json()
        json_data = await get_permission(json_data)
        ads = await get_ads(int(self.request.match_info['ads_id']), self.request['session'])
        if not (json_data['username'] == ads.username):
            raise web.HTTPUnauthorized(
                text=json.dumps({
                    'status': 'error',
                    'message': 'wrong user'
                }),
                content_type='application/json'
            )
        await self.request['session'].delete(ads)
        await self.request['session'].commit()
        return web.json_response({
            'status': 'delete ok'
        })

class UserView(web.View):

    async def post(self):
        json_data = await self.request.json()
        password = json_data['password']
        password = hash_password(password)
        json_data['password'] = password
        new_user = User(**json_data)
        self.request['session'].add(new_user)
        try:
            await self.request['session'].commit()
        except IntegrityError as err:
            raise web.HTTPConflict(
                text=json.dumps({
                    'error': 'user already exist'
                }),
                content_type='application/json'
            )
        return web.json_response({
            'id': new_user.id,
            'email': new_user.email
        })

    async def get(self):

        user = await get_user(int(self.request.match_info['user_id']), self.request['session'])
        return web.json_response({
            'id': user.id,
            'email': user.email
        })

    async def patch(self):

        json_data = await self.request.json()
        password = json_data['password']
        password = hash_password(password)
        json_data['password'] = password
        user = await get_user(int(self.request.match_info['user_id']), self.request['session'])
        for field, value in json_data.items():
            setattr(user, field, value)
        self.request['session'].add(user)
        await self.request['session'].commit()
        return web.json_response({
            'id': user.id,
            'email': user.email
        })

app.cleanup_ctx.append(app_context)
app.middlewares.append(session_middleware)
app.add_routes([
    web.post('/user/', UserView),
    web.get('/user/{user_id:\d+}', UserView),
    web.patch('/user/{user_id:\d+}', UserView),
    web.post('/ads/', AdsView),
    web.get('/ads/{ads_id:\d+}', AdsView),
    web.patch('/ads/{ads_id:\d+}', AdsView),
    web.delete('/ads/{ads_id:\d+}', AdsView)
])

if __name__ == '__main__':
    web.run_app(app)