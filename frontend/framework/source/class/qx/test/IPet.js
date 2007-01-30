/*
#require(qx.Interface)
#require(qx.test.IHumanlike)
#require(qx.test.IPlayable)
*/

qx.Interface.define("qx.test.IPet",
{
  extend : [
    qx.test.IHumanlike,
    qx.test.IPlayable
  ],

  members :
  {
    smooch : function() {}
  }
});
