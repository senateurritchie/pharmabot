import unittest
from EventDispatcher import EventDispatcher, Event

class AppDispatcher(EventDispatcher):
	def __init__(self):
		super().__init__()

	def on_launch(self,e:Event):
		print("on_launch")

	def on_pause(self,e:Event):
		print("on_pause")

	def on_resume(self,e:Event):
		print("on_resume")

class EventDispatcherTest(unittest.TestCase):
	"""Test case utilisé pour tester le fonctionnement de la class EventDispatcher."""

	def setUp(self):
		self.dispatcher = AppDispatcher();


	def test_hasEvent(self):
		self.assertEqual(self.dispatcher.hasEvent("launch"),True)
		self.assertEqual(self.dispatcher.hasEvent("pause"),True)
		self.assertEqual(self.dispatcher.hasEvent("resume"),True)

	def test_on(self):
		def cbk(e:Event):
			pass

		self.dispatcher.on("my custom event",cbk)
		self.assertEqual(self.dispatcher.hasEvent("my custom event"),True)


	def test_off(self):
		def cbk(e:Event):
			pass

		self.dispatcher.off("my custom event")
		self.assertEqual(self.dispatcher.hasEvent("my custom event"),False)

	def test_dispatch(self):
		def cbk(e:Event):
			self.assertEqual(e.data,"launched")

		self.dispatcher.on("launch",cbk)
		self.dispatcher.dispatch("launch","launched")

	def test_once(self):
		def cbk(e:Event):
			pass

		def cbk2(e:Event):
			pass

		eventname = "my custom event 2"
		self.dispatcher.once(eventname,cbk)
		self.dispatcher.once(eventname,cbk2)
		self.assertEqual(self.dispatcher.hasEvent(eventname),True)
		self.dispatcher.dispatch(eventname,"launched")
		self.assertEqual(self.dispatcher.hasEvent(eventname),False)

		eventname = "my custom event 3"
		self.dispatcher.once(eventname,cbk)
		self.dispatcher.on(eventname,cbk2)
		self.assertEqual(self.dispatcher.hasEvent(eventname),True)
		self.dispatcher.dispatch(eventname,"launched")
		self.assertEqual(self.dispatcher.hasEvent(eventname),True)

		

