#!/usr/bin/env python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# Module to fetch content from yum repos
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import logging
import threading

from grinder.GrinderCallback import ProgressReport

LOG = logging.getLogger(__name__)

class ProgressTracker(object):
    """
    Responsible for tracking progress information for all download objects
    Tracks total size versus amount downloaded
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.items = {}
        self.total_size_bytes = 0
        self.remaining_bytes = self.total_size_bytes
        self.total_num_items = 0
        self.remaining_num_items = 0
        self.type_info = {}

    def get_progress(self):
        self.lock.acquire()
        try:
            progress = {}
            progress["total_size_bytes"] = self.total_size_bytes
            progress["remaining_bytes"] = self.remaining_bytes
            progress["total_num_items"] = self.total_num_items
            progress["remaining_num_items"] = self.remaining_num_items
            progress["type_info"] = self.type_info.copy()
            return progress
        finally:
            self.lock.release()

    def add_item(self, fetchURL, size, item_type):
        """
        @param fetchURL: unique URL identifying where to fetch this item
        @type fetchURL: str

        @param size: expected size, 0 if unknown
        @type size: int

        @param item_type: type of item being fetch, example could be "rpm"
        @type item_type: str
        """
        self.lock.acquire()
        try:
            if size < 0:
                size = 0
            # Total Information for all Items
            self.total_size_bytes += size
            self.remaining_bytes = self.total_size_bytes

            self.total_num_items += 1
            self.remaining_num_items += 1

            # Account for Group info based on type of items, (rpm, drpm, etc)
            # Using older term of 'size_left', 'total_count', 'items_left' to avoid breaking
            # expectations Katello has.
            if not self.type_info.has_key(item_type):
                self.type_info[item_type] = {}
                self.type_info[item_type]["total_size_bytes"] = 0
                self.type_info[item_type]["size_left"] = 0
                self.type_info[item_type]["total_count"] = 0
                self.type_info[item_type]["items_left"] = 0
                self.type_info[item_type]["num_success"] = 0
                self.type_info[item_type]["num_error"] = 0
            self.type_info[item_type]["total_size_bytes"] += size
            self.type_info[item_type]["size_left"] += size
            self.type_info[item_type]["total_count"] += 1
            self.type_info[item_type]["items_left"] += 1

            # Account for Individual Item Information
            # Note: If fetchURL already existed it is overwritten
            self.items[fetchURL] = {}
            self.items[fetchURL]["total_size_bytes"] = size
            self.items[fetchURL]["remaining_bytes"] = self.items[fetchURL]["total_size_bytes"]
            self.items[fetchURL]["item_type"] = item_type
        finally:
            self.lock.release()

    def item_complete(self, fetchURL, status):
        """
        @param fetchURL: url of an item
        @type fetchURL: str

        @param status: True means successful transfer, False means an error occurred
        @type status: boolean
        """
        # This may be called to mark an item errored out and is complete
        # it's progress from a tracking perspective should be fully realized
        # 
        # Typically the curl PROGRESSFUNCTION callback will be called to adjust the
        # remaining_bytes to 0 for successful downloads.
        #
        # Also note, some items will be downloaded where we don't know the size
        # for those cases we will not adjust the progress since we don't know what we are tracking.
        self.lock.acquire()
        try:
            if not self.items.has_key(fetchURL):
                return
            item_type = self.items[fetchURL]["item_type"]
            prev_remaining_bytes = self.items[fetchURL]["remaining_bytes"]
            if prev_remaining_bytes > 0:
                # Adjust for incomplete transfers which are now finished
                # Remember to remove their remaining bytes from our counters
                self.remaining_bytes -= prev_remaining_bytes
                self.type_info[item_type]["size_left"] -= prev_remaining_bytes

            self.type_info[item_type]["items_left"] -= 1
            if status:
                self.type_info[item_type]["num_success"] += 1
            else:
                self.type_info[item_type]["num_error"] += 1

            del self.items[fetchURL]
            self.remaining_num_items -= 1
            #if itemInfo.has_key("size")  and itemInfo['size'] is not None and itemInfo['size'] >= 0:
            #    self.sizeLeft = self.sizeLeft - int(itemInfo['size'])
            #    if itemInfo.has_key("item_type"):
            #        item_type = itemInfo["item_type"]
            #        if not self.details[item_type].has_key("size_left"):
            #            self.details[item_type]["size_left"] = self.details[item_type]["total_size_bytes"] - int(itemInfo['size'])
            #        else:
            #            self.details[item_type]["size_left"] -= int(itemInfo['size'])
            #if itemInfo.has_key("item_type"):
            #    item_type = itemInfo["item_type"]
            #    if not self.details[item_type].has_key("items_left"):
            #        self.details[item_type]["items_left"] = self.details[item_type]["total_count"] - 1
            #    else:
            #        self.details[item_type]["items_left"] -= 1
            #    if status != BaseFetch.STATUS_ERROR:
            #        # Mark success for item
            #        if not self.details[item_type].has_key("num_success"):
            #            self.details[item_type]["num_success"] = 1
            #        else:
            #            self.details[item_type]["num_success"] += 1
            #    else:
            #        # Mark failure
            #        if not self.details[item_type].has_key("num_error"):
            #            self.details[item_type]["num_error"] = 1
            #        else:
            #            self.details[item_type]["num_error"] += 1
        finally:
            self.lock.release()

    def update_progress_downloaded(self, fetchURL, download_total, downloaded):
        """
        @param fetchURL url of the item, must be unique against all known items being downloaded
        @type fetchURL: str

        @param download_total expected total number of bytes for this item
        @type download_total: int

        @param downloaded number of bytes downloaded up till now for this item
        @type downloaded: int
        """
        # This method is used to note progress made while a specific item is being downloaded
        # Example, it can note that 100kb of a file has been downloaded.  
        # The other piece of the progress reporting is when the item completes, which is handled with item_complete
        self.lock.acquire()
        try:
            if not self.items.has_key(fetchURL):
                return
            item_type = self.items[fetchURL]["item_type"]
            prev_remaining_bytes = self.items[fetchURL]["remaining_bytes"]
            delta_bytes = prev_remaining_bytes - (downloaded_total - downloaded)
            if delta_bytes < 0:
                LOG.error("Transferred negative bytes <%s> for: %s download_total=<%s>, downloaded=<%s>" % \
                        (delta_bytes, fetchURL, download_total, downloaded))
                return

            self.items[fetchURL]["remaining_bytes"] = downloaded_total - downloaded
            # Adjust cumulative remaining bytes for all items
            self.remaining_bytes -= delta_bytes

            # Adjust remaining bytes for all of this type of item
            self.type_info[item_type]["remaining_bytes"] -= delta_bytes
        finally:
            self.lock.release()

