# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )
#

PKG = grinder
SPEC = $(PKG).spec
FEDORAHOSTEDGRINDER = fedorahosted.org:grinder
TITODIR = /tmp/tito

release : srpm 
	scp `find $(TITODIR) -name \*$(PKG)\*.src.rpm` $(FEDORAHOSTEDGRINDER)
	scp `find $(TITODIR) -name \*$(PKG)\*.tar.gz|grep -v git` $(FEDORAHOSTEDGRINDER)
	scp $(SPEC) $(FEDORAHOSTEDGRINDER)

srpm	:
	rm -rf $(TITODIR)
	tito build --srpm


clean :
	rm -rf src/dist
	rm -rf src/build
	rm -rf src/$(PKG).egg-info

.PHONY : clean