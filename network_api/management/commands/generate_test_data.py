from django.core.management.base import BaseCommand
from network_api.models import (
    Computer, Department, User, Software, Equipment,
    Network, HostComputer, UserComputer, SoftwareComputer,
    NetworkComputer, Server, ServerNetwork
)
import random
from datetime import date, timedelta
from faker import Faker

fake = Faker('ru_RU')


class Command(BaseCommand):
    help = 'Генерирует тестовые данные'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--computers', type=int, default=500)

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Очистка данных...')
            self._clear_data()

        self.stdout.write('Начало генерации...')

        departments = self._create_departments(15)
        self.stdout.write(f'[+] Отделы: {len(departments)}')

        equipment = self._create_equipment()
        self.stdout.write(f'[+] Оборудование: {len(equipment)}')

        networks = self._create_networks(20, equipment)
        self.stdout.write(f'[+] Сети: {len(networks)}')

        computers = self._create_computers(options['computers'], departments)
        self.stdout.write(f'[+] Компьютеры: {len(computers)}')

        users = self._create_users(300, departments)
        self.stdout.write(f'[+] Пользователи: {len(users)}')

        uc_count = self._create_user_computers(users, computers)
        self.stdout.write(f'[+] Связи User-Computer: {uc_count}')

        nc_count = self._create_network_computers(computers, networks)
        self.stdout.write(f'[+] Связи Network-Computer: {nc_count}')

        servers = self._create_servers(10)
        self.stdout.write(f'[+] Серверы: {len(servers)}')

        sn_count = self._create_server_networks(servers, networks)
        self.stdout.write(f'[+] Связи Server-Network: {sn_count}')

        hosts = self._create_host_computers(25, departments)
        self.stdout.write(f'[+] Хост-компьютеры: {len(hosts)}')

        software = self._create_software()
        sw_count = self._install_software(computers, software)
        self.stdout.write(f'[+] Установки ПО: {sw_count}')

        self.stdout.write(self.style.SUCCESS('\n[+] Генерация завершена!'))

    def _clear_data(self):
        NetworkComputer.objects.all().delete()
        SoftwareComputer.objects.all().delete()
        UserComputer.objects.all().delete()
        ServerNetwork.objects.all().delete()
        Network.objects.all().delete()
        Computer.objects.all().delete()
        User.objects.all().delete()
        Server.objects.all().delete()
        HostComputer.objects.all().delete()
        Department.objects.all().delete()

    def _create_equipment(self):
        equipment_list = [
            {'type': 'Cisco Catalyst 2960', 'bandwidth': 1000, 'port_count': 24, 'setup_date': date(2023, 1, 15)},
            {'type': 'Cisco Catalyst 9300', 'bandwidth': 10000, 'port_count': 48, 'setup_date': date(2023, 3, 20)},
            {'type': 'MikroTik RB750', 'bandwidth': 1000, 'port_count': 8, 'setup_date': date(2023, 2, 10)},
            {'type': 'D-Link DES-1005A', 'bandwidth': 100, 'port_count': 4, 'setup_date': date(2022, 11, 5)},
            {'type': 'Ubiquiti UniFi', 'bandwidth': 1000, 'port_count': 16, 'setup_date': date(2023, 5, 12)},
        ]

        equipment_objs = []
        for eq in equipment_list:
            obj, created = Equipment.objects.get_or_create(
                type=eq['type'],
                defaults={
                    'bandwidth': eq['bandwidth'],
                    'port_count': eq['port_count'],
                    'setup_date': eq['setup_date']
                }
            )
            equipment_objs.append(obj)
        return equipment_objs

    def _create_networks(self, count, equipment):
        networks = []

        if not equipment:
            self.stdout.write(self.style.ERROR('[-] Нет оборудования для создания сетей!'))
            return networks

        for i in range(count):
            vlan = 10 + i * 10
            third_octet = 10 + i

            network = Network.objects.create(
                subnet_mask='255.255.255.0',
                vlan=vlan,
                ip_range=f'192.168.{third_octet}.0/24',
                equipment=random.choice(equipment)
            )
            networks.append(network)

        return networks

    def _create_departments(self, count):
        departments = []
        for i in range(count):
            dept = Department.objects.create(
                room_number=100 + i,
                internal_phone=1000 + i,
                employee_count=random.randint(5, 20),
                employee_phones=[]
            )
            departments.append(dept)
        return departments

    def _create_computers(self, count, departments):
        computers = []
        models = ['Dell Optiplex', 'HP EliteDesk', 'Lenovo ThinkCentre']
        oss = ['Windows 10 Pro', 'Windows 11 Pro', 'Ubuntu 22.04']

        for i in range(count):
            computer = Computer.objects.create(
                serial_number=random.randint(100000, 999999),
                model=random.choice(models),
                os=random.choice(oss),
                inventory_number=random.randint(1000, 9999),
                department=random.choice(departments) if random.random() > 0.3 else None
            )
            computers.append(computer)
        return computers

    def _create_users(self, count, departments):
        users = []
        for i in range(count):
            user = User.objects.create(
                full_name=fake.name(),
                phone=fake.phone_number(),
                email=fake.email(),
                position_id=random.randint(1, 5),
                department=random.choice(departments) if random.random() > 0.2 else None
            )
            users.append(user)
        return users

    def _create_user_computers(self, users, computers):
        count = 0
        for user in users[:100]:
            num = random.randint(0, 2)
            assigned = random.sample(computers, min(num, len(computers)))
            for comp in assigned:
                _, created = UserComputer.objects.get_or_create(user=user, computer=comp)
                if created:
                    count += 1
        return count

    def _create_network_computers(self, computers, networks):
        count = 0
        for computer in random.sample(computers, min(300, len(computers))):
            num = random.randint(0, 2)
            assigned = random.sample(networks, min(num, len(networks)))
            for net in assigned:
                _, created = NetworkComputer.objects.get_or_create(
                    network=net,
                    computer=computer,
                    defaults={
                        'ip_address': f'192.168.{net.vlan // 10}.{random.randint(10, 250)}',
                        'mac_address': ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)]),
                        'speed': random.choice([100, 1000])
                    }
                )
                if created:
                    count += 1
        return count

    def _create_servers(self, count):
        servers = []
        for i in range(count):
            server = Server.objects.create(
                port=random.randint(1024, 65535),
                hostname=f'server-{i + 1}',
                connection_date=date.today() - timedelta(days=random.randint(30, 365)),
                location=random.choice(['ЦОД-1', 'ЦОД-2'])
            )
            servers.append(server)
        return servers

    def _create_server_networks(self, servers, networks):
        count = 0
        for server in servers:
            num = random.randint(1, 2)
            assigned = random.sample(networks, min(num, len(networks)))
            for net in assigned:
                _, created = ServerNetwork.objects.get_or_create(server=server, network=net)
                if created:
                    count += 1
        return count

    def _create_host_computers(self, count, departments):
        hosts = []

        for i in range(count):
            department = random.choice(departments) if departments and random.random() > 0.5 else None

            mac = ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)])

            host = HostComputer.objects.create(
                hostname=f'host-{i + 1}',
                ip_address=f'10.0.{random.randint(1, 254)}.{random.randint(1, 254)}',
                mac_address=mac,
                department=department
            )
            hosts.append(host)

        return hosts

    def _create_software(self):
        software_list = [
            {'name': 'Windows 10 Pro', 'version': '22H2', 'license': 'Commercial', 'vendor': 'Microsoft'},
            {'name': 'Office 2021', 'version': '2021', 'license': 'Commercial', 'vendor': 'Microsoft'},
            {'name': '1С:Предприятие', 'version': '8.3', 'license': 'Commercial', 'vendor': '1С'},
            {'name': 'Kaspersky', 'version': '12', 'license': 'Commercial', 'vendor': 'Лаборатория Касперского'},
            {'name': 'Ubuntu', 'version': '22.04', 'license': 'Open Source', 'vendor': 'Canonical'},
        ]

        software_objs = []
        for sw in software_list:
            obj, created = Software.objects.get_or_create(
                name=sw['name'],
                version=sw['version'],
                defaults={
                    'license': sw['license'],
                    'vendor': sw['vendor']
                }
            )
            software_objs.append(obj)
        return software_objs

    def _install_software(self, computers, software):
        count = 0
        for computer in random.sample(computers, min(400, len(computers))):
            num = random.randint(1, 4)
            installed = random.sample(software, min(num, len(software)))
            for sw in installed:
                _, created = SoftwareComputer.objects.get_or_create(software=sw, computer=computer)
                if created:
                    count += 1
        return count