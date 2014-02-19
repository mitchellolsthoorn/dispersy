from random import random
from unittest.case import skip

from ..logger import get_logger
from .debugcommunity.community import DebugCommunity
from .debugcommunity.node import DebugNode
from .dispersytestclass import DispersyTestFunc, call_on_dispersy_thread
logger = get_logger(__name__)


class TestSync(DispersyTestFunc):

    def _create_nodes_messages(self, type="create_full_sync_text"):
        node = DebugNode(self._community)
        node.init_socket()
        node.init_my_member()

        other = DebugNode(self._community)
        other.init_socket()
        other.init_my_member()

        # SELF creates messages
        messages = [getattr(other, type)("Message %d" % i, i + 10) for i in xrange(30)]
        self._dispersy._store(messages)

        return node, other, messages


    @call_on_dispersy_thread
    def test_modulo(self):
        """
        OTHER creates several messages, NODE asks for specific modulo to sync and only those modulo
        may be sent back.
        """
        node, other, messages = self._create_nodes_messages()

        for modulo in xrange(0, 10):
            for offset in xrange(0, modulo):
                # global times that we should receive
                global_times = [message.distribution.global_time for message in messages if (message.distribution.global_time + offset) % modulo == 0]

                sync = (1, 0, modulo, offset, [])
                other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", sync, 42, 110), node)

                responses = node.receive_messages(names=[u"full-sync-text"])
                response_times = [message.distribution.global_time for _, message in responses]

                self.assertEqual(sorted(global_times), sorted(response_times))


    @call_on_dispersy_thread
    def test_range(self):
        node, other, messages = self._create_nodes_messages()

        for time_low in xrange(1, 11):
            for time_high in xrange(20, 30):
                # global times that we should receive
                global_times = [message.distribution.global_time for message in messages if time_low <= message.distribution.global_time <= time_high]

                sync = (time_low, time_high, 1, 0, [])
                other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", sync, 42, 110), node)

                responses = node.receive_messages(names=[u"full-sync-text"])
                response_times = [message.distribution.global_time for _, message in responses]

                self.assertEqual(sorted(global_times), sorted(response_times))


    @call_on_dispersy_thread
    def test_in_order(self):
        node, other, messages = self._create_nodes_messages(type='create_in_order_text')
        global_times = [message.distribution.global_time for message in messages]

        # send an empty sync message to obtain all messages ASC order
        other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", (min(global_times), 0, 1, 0, []), 42, max(global_times)), node)

        for global_time in global_times:
            _, message = node.receive_message(names=[u"ASC-text"])
            self.assertEqual(message.distribution.global_time, global_time)


    @call_on_dispersy_thread
    def test_out_order(self):
        node, other, messages = self._create_nodes_messages(type='create_out_order_text')
        global_times = [message.distribution.global_time for message in messages]

        # send an empty sync message to obtain all messages DESC order
        other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", (min(global_times), 0, 1, 0, []), 42, max(global_times)), node)

        for global_time in reversed(global_times):
            _, message = node.receive_message(names=[u"DESC-text"])
            self.assertEqual(message.distribution.global_time, global_time)


    @call_on_dispersy_thread
    def test_random_order(self):
        node, other, messages = self._create_nodes_messages(type='create_random_order_text')
        global_times = [message.distribution.global_time for message in messages]

        # send an empty sync message to obtain all messages in RANDOM order
        other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", (min(global_times), 0, 1, 0, []), 42, max(global_times)), node)

        received_times = [message.distribution.global_time
                          for _, message
                          in node.receive_messages(names=[u"RANDOM-text"])]

        self.assertNotEqual(received_times, sorted(global_times))
        self.assertNotEqual(received_times, sorted(global_times, reverse=True))


    @call_on_dispersy_thread
    def test_mixed_order(self):
        node = DebugNode(self._community)
        node.init_socket()
        node.init_my_member()

        other = DebugNode(self._community)
        other.init_socket()
        other.init_my_member()

        # OTHER creates messages
        in_order_messages = [other.create_in_order_text("Message %d" % i, i + 10) for i in xrange(0, 30, 3)]
        out_order_messages = [other.create_out_order_text("Message %d" % i, i + 10) for i in xrange(1, 30, 3)]
        random_order_messages = [other.create_random_order_text("Message %d" % i, i + 10) for i in xrange(2, 30, 3)]

        self._dispersy._store(in_order_messages)
        self._dispersy._store(out_order_messages)
        self._dispersy._store(random_order_messages)

        # send an empty sync message to obtain all messages ALL messages
        other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", (1, 0, 1, 0, []), 42, 42), node)
        yield 0.1

        received = node.receive_messages(names=[u"ASC-text", u"DESC-text", u"RANDOM-text"])

        # all ASC-text must be received in-order of their global time (low to high)
        received_in_order = [message.distribution.global_time for _, message in received if message.name == u"ASC-text"]
        self.assertEqual(received_in_order, sorted(message.distribution.global_time for message in in_order_messages))

        # all DESC-text must be received in reversed order of their global time (high to low)
        received_out_order = [message.distribution.global_time for _, message in received if message.name == u"DESC-text"]
        self.assertEqual(received_out_order, sorted([message.distribution.global_time for message in out_order_messages], reverse=True))

        # all RANDOM-text must NOT be received in (reversed) order of their global time
        received_random_order = [message.distribution.global_time for _, message in received if message.name == u"RANDOM-text"]
        self.assertNotEqual(received_random_order, sorted([message.distribution.global_time for message in random_order_messages]))
        self.assertNotEqual(received_random_order, sorted([message.distribution.global_time for message in random_order_messages], reverse=True))

    @call_on_dispersy_thread
    def test_priority_order(self):
        node = DebugNode(self._community)
        node.init_socket()
        node.init_my_member()

        other = DebugNode(self._community)
        other.init_socket()
        other.init_my_member()

        # OTHER creates messages
        high_priority_messages = [other.create_high_priority_text("Message %d" % i, i + 10) for i in xrange(0, 30, 3)]
        low_priority_messages = [other.create_low_priority_text("Message %d" % i, i + 10) for i in xrange(1, 30, 3)]
        medium_priority_messages = [other.create_medium_priority_text("Message %d" % i, i + 10) for i in xrange(2, 30, 3)]

        self._dispersy._store(high_priority_messages)
        self._dispersy._store(low_priority_messages)
        self._dispersy._store(medium_priority_messages)

        # send an empty sync message to obtain all messages ALL messages
        other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", (1, 0, 1, 0, []), 42, 42), node)
        yield 0.1

        received = node.receive_messages(names=[u"high-priority-text", u"low-priority-text", u"medium-priority-text"])

        # the first should be the high-priority-text
        offset = 0
        self.assertEqual([message.name for _, message in received[offset:offset + len(high_priority_messages)]],
                         ["high-priority-text"] * len(high_priority_messages))

        # the second should be the medium-priority-text
        offset += len(high_priority_messages)
        self.assertEqual([message.name for _, message in received[offset:offset + len(medium_priority_messages)]],
                         ["medium-priority-text"] * len(medium_priority_messages))

        # last should be the low-priority-text
        offset += len(medium_priority_messages)
        self.assertEqual([message.name for _, message in received[offset:offset + len(low_priority_messages)]],
                         ["low-priority-text"] * len(low_priority_messages))

    def _check_equal(self, member_database_id, message_database_id, global_times):
        times = [x for x, in self._dispersy.database.execute(u"SELECT global_time FROM sync WHERE community = ? AND member = ? AND meta_message = ?", (self._community.database_id, member_database_id, message_database_id))]
        times.sort()
        self.assertEqual(times, global_times)

    @call_on_dispersy_thread
    def test_last_1(self):
        message = self._community.get_meta_message(u"last-1-test")

        node = DebugNode(self._community)
        node.init_socket()
        node.init_my_member()

        other = DebugNode(self._community)
        other.init_socket()
        other.init_my_member()

        # send a message
        global_time = 10
        node.give_message(other.create_last_1_test("should be accepted (1)", global_time), other)
        self._check_equal(other.my_member.database_id, message.database_id, [global_time])

        # send a message, should replace current one
        global_time = 11
        node.give_message(other.create_last_1_test("should be accepted (2)", global_time), other)
        self._check_equal(other.my_member.database_id, message.database_id, [global_time])

        # send a message (older: should be dropped)
        node.give_message(other.create_last_1_test("should be dropped (1)", global_time - 1), other)
        self._check_equal(other.my_member.database_id, message.database_id, [global_time])

        # as proof for the drop, the newest message should be sent back
        yield 0.1
        _, message = other.receive_message(names=[u"last-1-test"])
        self.assertEqual(message.distribution.global_time, global_time)

    @call_on_dispersy_thread
    def test_last_9(self):
        message = self._community.get_meta_message(u"last-9-test")

        node = DebugNode(self._community)
        node.init_socket()
        node.init_my_member()

        other = DebugNode(self._community)
        other.init_socket()
        other.init_my_member()

        all_messages = [21, 20, 28, 27, 22, 23, 24, 26, 25]
        messages_so_far = []
        for global_time in all_messages:
            # send a message
            message = other.create_last_9_test(str(global_time), global_time)
            node.give_message(message, other)

            messages_so_far.append(global_time)
            messages_so_far.sort()

            self._check_equal(other.my_member.database_id, message.database_id, messages_so_far)

        for global_time in [11, 12, 13, 19, 18, 17]:
            # send a message (older: should be dropped)
            node.give_message(other.create_last_9_test(str(global_time), global_time), other)
            self._check_equal(other.my_member.database_id, message.database_id, messages_so_far)

        messages_so_far.sort()
        for global_time in [30, 35, 37, 31, 32, 34, 33, 36, 38, 45, 44, 43, 42, 41, 40, 39]:
            # send a message (should be added and old one removed)
            message = other.create_last_9_test(str(global_time), global_time)
            node.give_message(message, other)

            messages_so_far.pop(0)
            messages_so_far.append(global_time)
            messages_so_far.sort()

            self._check_equal(other.my_member.database_id, message.database_id, messages_so_far)

    @skip('TODO: emilon')
    @call_on_dispersy_thread
    def test_last_1_doublemember(self):
        """
        Normally the LastSyncDistribution policy stores the last N messages for each member that
        created the message.  However, when the DoubleMemberAuthentication policy is used, there are
        two members.

        This can be handled in two ways:

         1. The first member who signed the message is still seen as the creator and hence the last
            N messages of this member are stored.

         2. Each member combination is used and the last N messages for each member combination is
            used.  For example: when member A and B sign a message it will not count toward the
            last-N of messages signed by A and C (which is another member combination.)

        Currently we only implement option #2.  There currently is no parameter to switch between
        these options.
        """
        community = DebugCommunity.create_community(self._dispersy, self._my_member)
        message = community.get_meta_message(u"last-1-doublemember-text")

        # create node and ensure that SELF knows the node address
        nodeA = DebugNode(community)
        nodeA.init_socket()
        nodeA.init_my_member()

        # create node and ensure that SELF knows the node address
        nodeB = DebugNode(community)
        nodeB.init_socket()
        nodeB.init_my_member()

        # create node and ensure that SELF knows the node address
        nodeC = DebugNode(community)
        nodeC.init_socket()
        nodeC.init_my_member()

        # dump some junk data, TODO: should not use this btw in actual test...
        # self._dispersy.database.execute(u"INSERT INTO sync (community, meta_message, member, global_time) VALUES (?, ?, 42, 9)", (community.database_id, message.database_id))
        # sync_id = self._dispersy.database.last_insert_rowid
        # self._dispersy.database.execute(u"INSERT INTO reference_member_sync (member, sync) VALUES (42, ?)", (sync_id,))
        # self._dispersy.database.execute(u"INSERT INTO reference_member_sync (member, sync) VALUES (43, ?)", (sync_id,))
        #
        # self._dispersy.database.execute(u"INSERT INTO sync (community, meta_message, member, global_time) VALUES (?, ?, 4, 9)", (community.database_id, message.database_id))
        # sync_id = self._dispersy.database.last_insert_rowid
        # self._dispersy.database.execute(u"INSERT INTO reference_member_sync (member, sync) VALUES (4, ?)", (sync_id,))
        # self._dispersy.database.execute(u"INSERT INTO reference_member_sync (member, sync) VALUES (43, ?)", (sync_id,))

        # send a message
        global_time = 10
        other_global_time = global_time + 1
        messages = []
        messages.append(nodeA.create_last_1_doublemember_text(nodeB.my_member, "should be accepted (1)", global_time, sign=True))
        messages.append(nodeA.create_last_1_doublemember_text(nodeC.my_member, "should be accepted (1)", other_global_time, sign=True))
        nodeA.give_messages(messages)
        entries = list(self._dispersy.database.execute(u"SELECT sync.global_time, sync.member, double_signed_sync.member1, double_signed_sync.member2 FROM sync JOIN double_signed_sync ON double_signed_sync.sync = sync.id WHERE sync.community = ? AND sync.member = ? AND sync.meta_message = ?", (community.database_id, nodeA.my_member.database_id, message.database_id)))
        self.assertEqual(len(entries), 2)
        self.assertIn((global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeB.my_member.database_id), max(nodeA.my_member.database_id, nodeB.my_member.database_id)), entries)
        self.assertIn((other_global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeC.my_member.database_id), max(nodeA.my_member.database_id, nodeC.my_member.database_id)), entries)

        # send a message
        global_time = 20
        other_global_time = global_time + 1
        messages = []
        messages.append(nodeA.create_last_1_doublemember_text(nodeB.my_member, "should be accepted (2) @%d" % global_time, global_time, sign=True))
        messages.append(nodeA.create_last_1_doublemember_text(nodeC.my_member, "should be accepted (2) @%d" % other_global_time, other_global_time, sign=True))
        nodeA.give_messages(messages)
        entries = list(self._dispersy.database.execute(u"SELECT sync.global_time, sync.member, double_signed_sync.member1, double_signed_sync.member2 FROM sync JOIN double_signed_sync ON double_signed_sync.sync = sync.id WHERE sync.community = ? AND sync.member = ? AND sync.meta_message = ?", (community.database_id, nodeA.my_member.database_id, message.database_id)))
        self.assertEqual(len(entries), 2)
        self.assertIn((global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeB.my_member.database_id), max(nodeA.my_member.database_id, nodeB.my_member.database_id)), entries)
        self.assertIn((other_global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeC.my_member.database_id), max(nodeA.my_member.database_id, nodeC.my_member.database_id)), entries)

        # send a message (older: should be dropped)
        old_global_time = 8
        messages = []
        messages.append(nodeA.create_last_1_doublemember_text(nodeB.my_member, "should be dropped (1)", old_global_time, sign=True))
        messages.append(nodeA.create_last_1_doublemember_text(nodeC.my_member, "should be dropped (1)", old_global_time, sign=True))
        nodeA.give_messages(messages)
        entries = list(self._dispersy.database.execute(u"SELECT sync.global_time, sync.member, double_signed_sync.member1, double_signed_sync.member2 FROM sync JOIN double_signed_sync ON double_signed_sync.sync = sync.id WHERE sync.community = ? AND sync.member = ? AND sync.meta_message = ?", (community.database_id, nodeA.my_member.database_id, message.database_id)))
        self.assertEqual(len(entries), 2)
        self.assertIn((global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeB.my_member.database_id), max(nodeA.my_member.database_id, nodeB.my_member.database_id)), entries)
        self.assertIn((other_global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeC.my_member.database_id), max(nodeA.my_member.database_id, nodeC.my_member.database_id)), entries)

        yield 0.1
        nodeA.drop_packets()

        # send a message (older: should be dropped)
        old_global_time = 8
        messages = []
        messages.append(nodeB.create_last_1_doublemember_text(nodeA.my_member, "should be dropped (1)", old_global_time, sign=True))
        messages.append(nodeC.create_last_1_doublemember_text(nodeA.my_member, "should be dropped (1)", old_global_time, sign=True))
        nodeA.give_messages(messages)
        entries = list(self._dispersy.database.execute(u"SELECT sync.global_time, sync.member, double_signed_sync.member1, double_signed_sync.member2 FROM sync JOIN double_signed_sync ON double_signed_sync.sync = sync.id WHERE sync.community = ? AND sync.member = ? AND sync.meta_message = ?", (community.database_id, nodeA.my_member.database_id, message.database_id)))
        self.assertEqual(len(entries), 2)
        self.assertIn((global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeB.my_member.database_id), max(nodeA.my_member.database_id, nodeB.my_member.database_id)), entries)
        self.assertIn((other_global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeC.my_member.database_id), max(nodeA.my_member.database_id, nodeC.my_member.database_id)), entries)

        # as proof for the drop, the newest message should be sent back
        yield 0.1
        times = []
        _, message = nodeA.receive_message(names=[u"last-1-doublemember-text"])
        times.append(message.distribution.global_time)
        _, message = nodeA.receive_message(names=[u"last-1-doublemember-text"])
        times.append(message.distribution.global_time)
        self.assertEqual(sorted(times), [global_time, other_global_time])

        # send a message (older + different member combination: should be dropped)
        old_global_time = 9
        messages = []
        messages.append(nodeB.create_last_1_doublemember_text(nodeA.my_member, "should be dropped (2)", old_global_time, sign=True))
        messages.append(nodeC.create_last_1_doublemember_text(nodeA.my_member, "should be dropped (2)", old_global_time, sign=True))
        nodeA.give_messages(messages)
        entries = list(self._dispersy.database.execute(u"SELECT sync.global_time, sync.member, double_signed_sync.member1, double_signed_sync.member2 FROM sync JOIN double_signed_sync ON double_signed_sync.sync = sync.id WHERE sync.community = ? AND sync.member = ? AND sync.meta_message = ?", (community.database_id, nodeA.my_member.database_id, message.database_id)))
        self.assertEqual(len(entries), 2)
        self.assertIn((global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeB.my_member.database_id), max(nodeA.my_member.database_id, nodeB.my_member.database_id)), entries)
        self.assertIn((other_global_time, nodeA.my_member.database_id, min(nodeA.my_member.database_id, nodeC.my_member.database_id), max(nodeA.my_member.database_id, nodeC.my_member.database_id)), entries)

    @skip('TODO: emilon')
    @call_on_dispersy_thread
    def test_last_1_doublemember_unique_member_global_time(self):
        """
        Even with double member messages, the first member is the creator and may only have one
        message for each global time.
        """
        community = DebugCommunity.create_community(self._dispersy, self._my_member)
        message = community.get_meta_message(u"last-1-doublemember-text")

        # create node and ensure that SELF knows the node address
        nodeA = DebugNode(community)
        nodeA.init_socket()
        nodeA.init_my_member()

        # create node and ensure that SELF knows the node address
        nodeB = DebugNode(community)
        nodeB.init_socket()
        nodeB.init_my_member()

        # create node and ensure that SELF knows the node address
        nodeC = DebugNode(community)
        nodeC.init_socket()
        nodeC.init_my_member()

        # send two messages
        global_time = 10
        messages = []
        messages.append(nodeA.create_last_1_doublemember_text(nodeB.my_member, "should be accepted (1.1)", global_time, sign=True))
        messages.append(nodeA.create_last_1_doublemember_text(nodeC.my_member, "should be accepted (1.2)", global_time, sign=True))

        # we NEED the messages to be handled in one batch.  using the socket may change this
        nodeA.give_messages(messages)

        times = [x for x, in self._dispersy.database.execute(u"SELECT global_time FROM sync WHERE community = ? AND member = ? AND meta_message = ?", (community.database_id, nodeA.my_member.database_id, message.database_id))]
        self.assertEqual(times, [global_time])

    @call_on_dispersy_thread
    def test_performance(self):
        """
        OTHER creates 10k messages and NODE sends 100 sync requests.
        """
        node = DebugNode(self._community)
        node.init_socket()
        node.init_my_member()

        other = DebugNode(self._community)
        other.init_socket()
        other.init_my_member()

        # SELF creates 10k messages
        with self._dispersy.database:
            for i in xrange(10000):
                msg = other.create_full_sync_text("test performance data #%d" % i, i + 10)
                other.give_message(msg, other)

        # NODE creates 100 sync requests
        for i in xrange(100):
            m = int(random() * 10) + 1
            o = min(m - 1, int(random() * 10))
            sync = (1, 0, m, o, [])
            other.give_message(node.create_dispersy_introduction_request(other.my_candidate, node.lan_address, node.wan_address, False, u"unknown", sync, 42, 10), node)
