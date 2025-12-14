from rest_framework import serializers
from .models import (
    Department, Computer, User, Software, Network, NetworkComputer,
    Equipment, HostComputer, Server, SoftwareComputer, UserComputer, ServerNetwork
)

class DepartmentSerializer(serializers.ModelSerializer):
    computers_count = serializers.SerializerMethodField()
    avg_computers_per_employee = serializers.SerializerMethodField()
    is_large_department = serializers.SerializerMethodField()

    host_computer_ip = serializers.CharField(
        source='hostcomputer.ip_address',
        read_only=True,
        allow_null=True
    )

    employee_phones = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list
    )

    # Для nested отображения
    hostcomputer = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Department
        fields = [
            'id', 'room_number', 'internal_phone',
            'employee_count', 'employee_phones',
            'computers_count', 'avg_computers_per_employee',
            'is_large_department', 'host_computer_ip', 'hostcomputer'
        ]
        read_only_fields = ['id', 'computers_count', 'avg_computers_per_employee',
                            'is_large_department', 'host_computer_ip']
        extra_kwargs = {
            'hostcomputer': {'required': False, 'allow_null': True}
        }

    def get_computers_count(self, obj):
        if hasattr(obj, 'computers_count'):
            return obj.computers_count
        return obj.computers.count() if hasattr(obj, 'computers') else 0

    def get_avg_computers_per_employee(self, obj):
        computers_count = self.get_computers_count(obj)
        if obj.employee_count > 0:
            return round(computers_count / obj.employee_count, 2)
        return 0

    def get_is_large_department(self, obj):
        return obj.employee_count > 10

    def validate_room_number(self, value):
        if value < 100 or value > 599:
            raise serializers.ValidationError(
                "Номер комнаты должен быть от 100 до 599"
            )
        return value

    def validate_employee_count(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "В отделе должен быть хотя бы 1 сотрудник"
            )
        if value > 20:
            raise serializers.ValidationError(
                "Слишком много сотрудников для одного отдела"
            )
        return value

    def validate_employee_phones(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("employee_phones должен быть списком")

        for phone in value:
            if not isinstance(phone, int):
                raise serializers.ValidationError(
                    f"Телефон '{phone}' должен быть числом"
                )
            if phone <= 0:
                raise serializers.ValidationError(
                    f"Телефон '{phone}' должен быть положительным числом"
                )
        return value

    def validate(self, attrs):
        room_number = attrs.get('room_number')
        employee_count = attrs.get('employee_count', 0)

        if employee_count > 10 and room_number < 50:
            raise serializers.ValidationError({
                'room_number': 'Крупные отделы размещаются в комнатах 50+'
            })
        return attrs

class ComputerSerializer(serializers.ModelSerializer):
    department_info = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    software_list = serializers.SerializerMethodField()
    network_speed = serializers.SerializerMethodField()

    class Meta:
        model = Computer
        fields = [
            'id', 'serial_number', 'model', 'os',
            'inventory_number', 'department', 'department_info',
            'users_count', 'software_list', 'network_speed'
        ]
        read_only_fields = ['department_info', 'users_count',
                            'software_list', 'network_speed']

    def get_department_info(self, obj):
        if obj.department:
            return f"Комната {obj.department.room_number} (тел: {obj.department.internal_phone})"
        return "Не назначен"

    def get_users_count(self, obj):
        return obj.users.count() if hasattr(obj, 'users') else 0

    def get_software_list(self, obj):
        if hasattr(obj, 'software'):
            return list(obj.software.values_list('name', flat=True))
        return []

    def get_network_speed(self, obj):
        if hasattr(obj, 'networkcomputer_set'):
            network_conn = obj.networkcomputer_set.first()
            return network_conn.speed if network_conn else 0
        return 0

    def validate_serial_number(self, value):
        instance = self.instance
        if instance:
            exists = Computer.objects.filter(
                serial_number=value
            ).exclude(id=instance.id).exists()
        else:
            exists = Computer.objects.filter(serial_number=value).exists()

        if exists:
            raise serializers.ValidationError("Компьютер с таким серийным номером уже существует")
        return value


class UserSerializer(serializers.ModelSerializer):
    department_room = serializers.CharField(
        source='department.room_number',
        read_only=True
    )
    computers_info = serializers.SerializerMethodField()
    can_manage_network = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone', 'email',
            'position_id', 'department', 'department_room',
            'computers_info', 'can_manage_network'
        ]
        read_only_fields = ['department_room', 'computers_info', 'can_manage_network']

    def get_computers_info(self, obj):
        if hasattr(obj, 'computers'):
            computers = obj.computers.all()
            return [
                {
                    'id': comp.id,
                    'model': comp.model,
                    'os': comp.os
                } for comp in computers
            ]
        return []

    def get_can_manage_network(self, obj):
        return obj.position_id in [1, 2]

    def validate_email(self, value):
        if not value.endswith(('@company.com', '@corp.com')):
            raise serializers.ValidationError(
                "Используйте корпоративную почту (@company.com или @corp.com)"
            )
        return value

    def validate(self, attrs):
        position_id = attrs.get('position_id')
        department = attrs.get('department')

        if position_id in [1, 2] and not department:
            raise serializers.ValidationError({
                'department': 'Руководители должны быть привязаны к отделу'
            })
        return attrs


class SoftwareSerializer(serializers.ModelSerializer):
    installed_count = serializers.SerializerMethodField()
    popular_os = serializers.SerializerMethodField()
    needs_license_renewal = serializers.SerializerMethodField()

    class Meta:
        model = Software
        fields = [
            'id', 'name', 'version', 'license', 'vendor',
            'installed_count', 'popular_os', 'needs_license_renewal'
        ]
        read_only_fields = ['installed_count', 'popular_os', 'needs_license_renewal']

    def get_installed_count(self, obj):
        return obj.computers.count() if hasattr(obj, 'computers') else 0

    def get_popular_os(self, obj):
        if hasattr(obj, 'computers'):
            os_list = obj.computers.values_list('os', flat=True).distinct()
            return list(os_list)
        return []

    def get_needs_license_renewal(self, obj):
        return 'trial' in obj.license.lower() or 'expired' in obj.license.lower()


class NetworkComputerSerializer(serializers.ModelSerializer):
    computer_model = serializers.CharField(source='computer.model', read_only=True)
    network_vlan = serializers.IntegerField(source='network.vlan', read_only=True)

    class Meta:
        model = NetworkComputer
        fields = ['id', 'network', 'computer', 'ip_address', 'mac_address',
                  'speed', 'computer_model', 'network_vlan']
        read_only_fields = ['computer_model', 'network_vlan']


class NetworkSerializer(serializers.ModelSerializer):
    equipment_port_count = serializers.IntegerField(
        source='equipment.port_count',
        read_only=True
    )
    equipment_type = serializers.CharField(
        source='equipment.type',
        read_only=True
    )

    network_computers = NetworkComputerSerializer(
        source='networkcomputer_set',
        many=True,
        read_only=True
    )

    class Meta:
        model = Network
        fields = [
            'id', 'subnet_mask', 'vlan', 'ip_range',
            'equipment', 'equipment_port_count', 'equipment_type',
            'network_computers'
        ]
        read_only_fields = ['equipment_port_count', 'equipment_type', 'network_computers']
        extra_kwargs = {
            'equipment': {'required': True}
        }


class EquipmentSerializer(serializers.ModelSerializer):
    type_of_bandwidth = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['id', 'type', 'bandwidth', 'port_count', 'setup_date', 'type_of_bandwidth']
        read_only_fields = ['type_of_bandwidth']

    def get_type_of_bandwidth(self, obj):
        if obj.bandwidth == 100:
            return 'Базовый интернет'
        elif obj.bandwidth == 1000:
            return 'Онлайн-игры'
        else:
            return 'Видеозвонки'


class HostComputerSerializer(serializers.ModelSerializer):
    department_room = serializers.CharField(
        source='department.room_number',
        read_only=True
    )

    class Meta:
        model = HostComputer
        fields = ['id', 'hostname', 'ip_address', 'mac_address',
                  'department', 'department_room']
        read_only_fields = ['department_room']


class ServerSerializer(serializers.ModelSerializer):
    networks_info = serializers.SerializerMethodField()

    class Meta:
        model = Server
        fields = ['id', 'port', 'hostname', 'connection_date',
                  'location', 'networks_info']
        read_only_fields = ['networks_info']

    def get_networks_info(self, obj):
        if hasattr(obj, 'networks'):
            return list(obj.networks.values_list('vlan', flat=True))
        return []


class SoftwareComputerSerializer(serializers.ModelSerializer):
    software_name = serializers.CharField(source='software.name', read_only=True)
    computer_model = serializers.CharField(source='computer.model', read_only=True)

    class Meta:
        model = SoftwareComputer
        fields = ['id', 'software', 'computer', 'software_name', 'computer_model']
        read_only_fields = ['software_name', 'computer_model']


class UserComputerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    computer_model = serializers.CharField(source='computer.model', read_only=True)

    class Meta:
        model = UserComputer
        fields = ['id', 'user', 'computer', 'user_name', 'computer_model']
        read_only_fields = ['user_name', 'computer_model']


class ServerNetworkSerializer(serializers.ModelSerializer):
    server_hostname = serializers.CharField(source='server.hostname', read_only=True)
    network_vlan = serializers.IntegerField(source='network.vlan', read_only=True)

    class Meta:
        model = ServerNetwork
        fields = ['id', 'server', 'network', 'server_hostname', 'network_vlan']
        read_only_fields = ['server_hostname', 'network_vlan']