import logging

from qiling.os.uefi.const import EFI_SUCCESS, EFI_NOT_FOUND, EFI_UNSUPPORTED, EFI_BUFFER_TOO_SMALL
from qiling.os.uefi.utils import read_int64, write_int64, check_and_notify_protocols
from qiling.os.uefi.UefiSpec import EFI_LOCATE_SEARCH_TYPE

# TODO: get rid of this
pointer_size = 8

def LocateHandles(context, params):
	SearchType = params["SearchType"]
	Protocol = params["Protocol"]

	# get all handles
	if SearchType == EFI_LOCATE_SEARCH_TYPE.AllHandles:
		handles = context.protocols.keys()

	# get all handles that support the specified protocol
	elif SearchType == EFI_LOCATE_SEARCH_TYPE.ByProtocol:
		handles = [handle for handle, guid_dic in context.protocols.items() if Protocol in guid_dic]

	else:
		handles = []

	return len(handles) * pointer_size, handles

def InstallProtocolInterface(context, params):
	handle = read_int64(context.ql, params["Handle"])

	if handle == 0:
		handle = context.heap.alloc(1)

	dic = context.protocols.get(handle, {})

	dic[params["Protocol"]] = params["Interface"]
	context.protocols[handle] = dic
	check_and_notify_protocols(context.ql)
	write_int64(context.ql, params["Handle"], handle)

	return EFI_SUCCESS

def ReinstallProtocolInterface(context, params):
	handle = params["Handle"]

	if handle not in context.protocols:
		return EFI_NOT_FOUND

	dic = context.protocols[handle]
	protocol = params["Protocol"]

	if protocol not in dic:
		return EFI_NOT_FOUND

	dic[protocol] = params["NewInterface"]

	return EFI_SUCCESS

def UninstallProtocolInterface(context, params):
	handle = params["Handle"]

	if handle not in context.protocols:
		return EFI_NOT_FOUND

	dic = context.protocols[handle]
	protocol = params["Protocol"]

	if protocol not in dic:
		return EFI_NOT_FOUND

	del dic[protocol]

	return EFI_SUCCESS

def HandleProtocol(context, params):
	handle = params["Handle"]
	protocol = params["Protocol"]
	interface = params['Interface']

	if handle in context.protocols:
		supported = context.protocols[handle]

		if protocol in supported:
			write_int64(context.ql, interface, supported[protocol])

			return EFI_SUCCESS

	return EFI_UNSUPPORTED

def LocateHandle(context, params):
	buffer_size, handles = LocateHandles(context, params)

	if len(handles) == 0:
		return EFI_NOT_FOUND

	ret = EFI_BUFFER_TOO_SMALL

	if read_int64(context.ql, params["BufferSize"]) >= buffer_size:
		ptr = params["Buffer"]

		for handle in handles:
			write_int64(context.ql, ptr, handle)
			ptr += pointer_size

		ret = EFI_SUCCESS

	write_int64(context.ql, params["BufferSize"], buffer_size)

	return ret

def LocateProtocol(context, params):
	protocol = params['Protocol']

	for handle, guid_dic in context.protocols.items():
		if "Handle" in params and params["Handle"] != handle:
			continue

		if protocol in guid_dic:
			# write protocol address to out variable Interface
			write_int64(context.ql, params['Interface'], guid_dic[protocol])
			return EFI_SUCCESS

	logging.warning(f'protocol with guid {protocol} not found')

	return EFI_NOT_FOUND
